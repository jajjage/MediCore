import uuid
from django.db import models
from django_tenants.utils import schema_context, get_tenant
from django.contrib.auth.models import Permission, Group
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)

from hospital.models import HospitalProfile


class StaffUserManager(BaseUserManager):
    def create_user(self, email, password, role, department, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        user = self.model(
            email=self.normalize_email(email),
            role=role,
            department=department,
            **extra_fields,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user



class Department(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    hospital = models.ForeignKey(HospitalProfile, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.name} - {self.hospital.hospital_name}"
    class Meta:
        db_table = "department"
    
# models.py
class StaffRole(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, unique=True)
    permissions = models.ManyToManyField(
        'auth.Permission',
        blank=True,
        related_name='staff_roles'
    )
    
    class Meta:
        db_table = "staff_staffrole"  # Updated to match actual table name

    def __str__(self):
        return self.name
class StaffMember(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    role = models.ForeignKey(StaffRole, on_delete=models.PROTECT)
    department = models.ForeignKey(Department, on_delete=models.PROTECT)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=True)
    
    objects = StaffUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["role", "department"]

    class Meta:
        db_table = "staff_user"
        permissions = [
            ("can_view_staff", "Can view staff members"),
            ("can_manage_staff", "Can manage staff members"),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

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