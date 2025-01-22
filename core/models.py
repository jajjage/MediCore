import uuid

from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    Group,
    PermissionsMixin,
)
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import connection, models

from hospital.models import HospitalProfile


class TenantMemberships(models.Model):
    ROLE_CHOICES = [
        ("ADMIN", "Admin"),
        ("STAFF", "Staff"),
        ("VIEWER", "Viewer"),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        "MyUser",
        on_delete=models.CASCADE,
        related_name="tenant_memberships"
    )
    tenant = models.ForeignKey("tenants.Client",  on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    groups = models.ManyToManyField(Group, blank=True )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "core_tenant_memberships"
        unique_together = ["user", "tenant"]
        indexes = [
            models.Index(fields=["tenant", "role"]),
        ]

class MyUserManager(BaseUserManager):
    def create_tenant_admin(self, email, password=None, **kwargs):
        if not email:
            raise ValueError("Users must have an email address")

        user = self.model(
            email=self.normalize_email(email),
            is_tenant_admin=True,
            **kwargs
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None):
        user = self.model(
            email=self.normalize_email(email),
            is_superuser=True,
            is_tenant_admin=True
        )
        user.set_password(password)
        user.save(using=self._db)
        return user


class MyUser(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=True)
    is_tenant_admin = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    objects = MyUserManager()

    USERNAME_FIELD = "email"

    class Meta:
        db_table = "core_user"

    def clean(self):
        if self.is_tenant_admin and not self.hospital:
            raise ValidationError("Tenant admin must be associated with a hospital")

        if self.hospital:
            try:
                profile = HospitalProfile.objects.get(tenant=self.hospital)
                if self.is_tenant_admin and profile.admin_user_id and profile.admin_user_id != self.id:
                    raise ValidationError("This hospital already has a primary admin")
            except HospitalProfile.DoesNotExist as err:
                raise ValidationError("Associated hospital has no profile") from err

    def has_tenant_access(self, schema_name):
        """Check if user has access to specific tenant."""
        cache_key = f"tenant_access_{self.id}_{schema_name}"
        cached_result = cache.get(cache_key)

        if cached_result is not None:
            return cached_result

        if (self.is_superuser and connection.schema_name == "public") or (self.is_tenant_admin and self.hospital and self.hospital.schema_name == schema_name):
            has_access = True
        else:
            has_access = self.tenant_permissions.filter(
                schema_name=schema_name
            ).exists()

        cache.set(cache_key, has_access, timeout=300)  # Cache for 5 minutes
        return has_access

    # def get_tenant_permissions(self, schema_name):
    #     """Get the permission type for a specific tenant."""
    #     if (self.is_superuser and connection.schema_name == "public") or (self.is_tenant_admin and self.hospital and self.hospital.schema_name == schema_name):
    #         return "ADMIN"
    #     else:
    #         try:
    #             permission = self.tenant_permissions.get(schema_name=schema_name)
    #         except TenantPermission.DoesNotExist:
    #             return None
    #         else:
    #             return permission.permission_type

    def has_perm(self, perm, obj=None):
        if connection.schema_name == "public":
            if self.is_superuser:
                app_label = perm.split(".")[0]
                return app_label in ["auth", "core", "tenants"]
            return False

        permission_type = self.get_tenant_permission_type(connection.schema_name)
        if permission_type == "ADMIN":
            return True
        if permission_type == "STAFF":
            # Add your staff permission logic here
            app_label = perm.split(".")[0]
            return app_label not in ["auth", "core", "tenants"]
        return False

    def has_module_perms(self, app_label):
        if connection.schema_name == "public":
            if self.is_superuser:
                return app_label in ["auth", "core", "tenants"]
            return False

        permission_type = self.get_tenant_permission_type(connection.schema_name)
        if permission_type == "ADMIN":
            return app_label not in ["auth", "core", "tenants"]
        if permission_type == "STAFF":
            # Add your staff module permission logic here
            return app_label not in ["auth", "core", "tenants"]
        return False
