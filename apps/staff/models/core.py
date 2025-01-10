import uuid

from django.contrib.auth.models import (
    AbstractUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from .departments import Department
from .staff_role import StaffRole


class StaffManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)

        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)

        user = self.model(email=email, **extra_fields)
        user.set_password(password)  # This is crucial - make sure password is being hashed
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)

class StaffMember(AbstractUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    hospital = models.ForeignKey(
        "hospital.HospitalProfile", on_delete=models.CASCADE, null=True, blank=True
    )
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    role = models.ForeignKey(
        StaffRole,
        on_delete=models.PROTECT,
        help_text=_("Role of the staff member in the department")
    )
    is_active = models.BooleanField(default=True)
    username = None  # Remove username field

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    objects = StaffManager()

    class Meta:
        db_table = "staff_member"
        indexes = [
            models.Index(fields=["email", "is_active"]),
            models.Index(fields=["hospital", "role"]),
            models.Index(fields=["first_name", "last_name"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(email__isnull=False),
                name="staff_email_not_null"
            )
        ]

    def __str__(self):
        return self.email

    def has_perm(self, perm, obj=None):
        """
        Override has_perm to check permissions from role instead of user_permissions.
        """
        if self.is_active:
            return perm in self.role.permissions.values_list("codename", flat=True)
        return False

    def has_perms(self, perm_list, obj=None):
        """
        Override has_perms to check permissions from role.
        """
        return all(self.has_perm(perm, obj) for perm in perm_list)

    def has_module_perms(self, app_label):
        """
        Override has_module_perms to check permissions from role.
        """
        if self.is_active:
            return self.role.permissions.filter(
                content_type__app_label=app_label
            ).exists()
        return False

    def has_role(self, role_codes):
        """
        Check if user has any of the specified role codes.
        """
        return self.role.code in role_codes

    def get_role_permissions(self):
        """
        Get all permissions associated with the user's role.
        """
        return self.role.permissions.all()

    def clean(self):
        if not self.email:
            raise ValidationError("Email is required")
        if not self.first_name or not self.last_name:
            raise ValidationError("Both first name and last name are required")

    @property
    def primary_department(self):
        """Get the user's primary department."""
        return self.department_memberships.filter(is_primary=True).first()

    def get_all_departments(self):
        """Get all departments the user belongs to."""
        return Department.objects.filter(staff_members__user=self,
                                      staff_members__is_active=True)

    def get_current_roles(self):
        """Get all active roles."""
        return self.department_memberships.filter(
            is_active=True
        ).values_list("role", flat=True).distinct()
