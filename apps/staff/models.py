import uuid

from django.contrib.auth.models import (
    AbstractUser,
    BaseUserManager,
)
from django.db import models


class StaffManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)


class Department(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    hospital = models.ForeignKey("hospital.HospitalProfile", on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "department"


class StaffRole(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, unique=True)
    permissions = models.ManyToManyField("auth.Permission", blank=True, related_name="staff_roles")

    class Meta:
        db_table = "staff_staffrole"

    def __str__(self):
        return self.name


class StaffMember(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    hospital = models.ForeignKey("hospital.HospitalProfile", on_delete=models.CASCADE, null=True, blank=True)   
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    role = models.ForeignKey(StaffRole, on_delete=models.SET_NULL, null=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=True)
    username = None  # Remove username field

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = StaffManager()

    groups = models.ManyToManyField(
        "auth.Group",
        related_name="staff_members",
        blank=True,
        help_text="The groups this user belongs to.",
        verbose_name="groups",
    )
    user_permissions = models.ManyToManyField(
        "auth.Permission",
        related_name="staff_members",
        blank=True,
        help_text="Specific permissions for this user.",
        verbose_name="user permissions",
    )

    class Meta:
        db_table = "staff_member"  # Explicitly set the table name
        permissions = [
            ("can_view_staff", "Can view staff members"),
            ("can_manage_staff", "Can manage staff members"),
        ]

    def __str__(self):
        return self.email

    def has_role(self, role_codes):
        """
        Check if user has any of the specified role codes
        """
        return self.role.code in role_codes

    def get_role_permissions(self):
        """
        Get all permissions associated with the user's role
        """
        return self.role.permissions.all()
