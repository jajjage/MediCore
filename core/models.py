from django.db import connection, models
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

    def create_hospital_admin(self, email, hospital, first_name, last_name, password=None):
        return self.create_user(
            email=email,
            first_name=first_name,
            last_name=last_name,
            hospital=hospital,
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
        Controls access to admin panel
        """
        if connection.schema_name == 'public':
            # Only superusers can access main domain admin
            return self.is_superuser
        else:
            # In tenant schemas, admin role can access tenant admin
            return self.is_admin and self.role == 'staff' and self.staff_role == 'admin'

    def has_perm(self, perm, obj=None):
        """
        Controls permissions in admin panel
        """
        if connection.schema_name == 'public':
            # In main domain, only superuser has full permissions
            if not self.is_superuser:
                # Block access to tenant-specific models
                if perm.startswith('tenant.'):
                    return False
            return self.is_superuser
        else:
            # In tenant schemas, admin has permissions for non-public apps
            return self.is_admin

    def has_module_perms(self, app_label):
        """
        Controls which apps are visible in admin
        """
        if connection.schema_name == 'public':
            if self.is_superuser:
                # Superuser can see all apps except tenant-specific ones
                return True
            return False
        else:
            # In tenant schemas, admin can only see tenant-specific apps
            return self.is_admin and app_label not in ['tenant', 'core']