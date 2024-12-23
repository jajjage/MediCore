from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser
from django.utils.translation import gettext_lazy as _

class MyUserManager(BaseUserManager):
    def create_user(self, email, role, password=None, staff_role=None, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address")
        if not role:
            raise ValueError("Users must have a role")

        # Validate staff_role based on role
        if role == 'staff' and not staff_role:
            raise ValueError("Staff must have a staff role")
        if role != 'staff' and staff_role:
            raise ValueError("Non-staff users cannot have a staff role")

        user = self.model(
            email=self.normalize_email(email),
            role=role,
            staff_role=staff_role,
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None):
        return self.create_user(
            email=email,
            role='staff',
            staff_role='admin',
            password=password,
            is_admin=True,
            is_superuser=True
        )

    def create_hospital_admin(self, email, first_name, last_name, password=None):
        return self.create_user(
            email=email,
            first_name=first_name,
            last_name=last_name,
            role='staff',
            staff_role='admin',
            password=password,
            is_admin=True
        )

class MyUser(AbstractBaseUser):
    ROLES = [
        ('staff', _('Staff')),
        ('patient', _('Patient')),
    ]

    STAFF_ROLES = [
        ('admin', _('Admin')),
        ('doctor', _('Doctor')),
        ('nurse', _('Nurse')),
        ('receptionist', _('Receptionist')),  # Added new role
    ]

    email = models.EmailField(
        verbose_name="email address",
        max_length=255,
        unique=True,
    )
    first_name = models.CharField(max_length=30, blank=True)  # Added name fields
    last_name = models.CharField(max_length=30, blank=True)
    role = models.CharField(max_length=10, choices=ROLES)
    staff_role = models.CharField(
        max_length=15,  # Increased length for new roles
        choices=STAFF_ROLES,
        null=True,
        blank=True
    )
    hospital = models.ForeignKey("tenants.Client", related_name='tenant_hospital',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = MyUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["role"]  # Removed date_of_birth as it wasn't defined

    class Meta:
        permissions = [
            ("can_view_patient_records", "Can view patient records"),
            ("can_edit_patient_records", "Can edit patient records"),
            ("can_manage_staff", "Can manage staff members"),
        ]

    def __str__(self):
        return f"{self.email} ({self.get_role_display()})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()
    
    @property
    def is_staff(self):
        """
        Determines admin interface access - only for hospital admins
        """
        return self.is_admin or (self.role == "staff" and self.staff_role == "admin")
    
    @property
    def can_access_patient_data(self):
        """
        Only doctors and nurses can access patient data
        """
        return (
            self.role == "staff" 
            and self.staff_role in ["doctor", "nurse"]
        )

    def has_perm(self, perm, obj=None):
        """
        Check permissions based on role
        """
        # For patient-related permissions
        if perm in ['view_patient_records', 'edit_patient_records']:
            return self.can_access_patient_data
            
        # For other admin permissions
        return self.is_admin or self.is_superuser

    def has_module_perms(self, app_label):
        if self.is_admin or self.is_superuser:
            return True
        return self.is_active and any(
            perm.codename.startswith(app_label)
            for perm in self.user_permissions.all()
        )