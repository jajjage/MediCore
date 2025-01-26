import uuid

from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.core.cache import cache
from django.db import connection, models

from hospital.models.hospital_members import HospitalMembership


class MyUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None):
        user = self.model(
            email=self.normalize_email(email),
            is_superuser=True,
            is_staff=True
        )
        user.set_password(password)
        user.save(using=self._db)
        return user


class MyUser(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    tenant = models.ManyToManyField("tenants.Client", through="hospital.HospitalMembership", related_name="users")
    first_name = models.CharField(max_length=150, blank=True)
    middle_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)

    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    objects = MyUserManager()

    USERNAME_FIELD = "email"

    class Meta:
        db_table = "core_user"
        indexes = [
            models.Index(fields=["email", "is_active"]),
            models.Index(fields=[ "phone_number"]),
            models.Index(fields=["first_name", "last_name"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(email__isnull=False),
                name="staff_email_not_null"
            )
        ]

    def clear_permission_cache(self):
        """Clear all cached permissions for this user."""
        keys = [
            f"user_perms_{self.id}_*",
            f"tenant_access_{self.id}_*",
            f"tenant_role_{self.id}_*",
        ]
        for key in keys:
            cache.delete_pattern(key)

    def has_tenant_access(self, schema_name):
        """Check if user has access to a specific tenant (with caching)."""
        cache_key = f"tenant_access_{self.id}_{schema_name}"
        cached_result = cache.get(cache_key)

        if cached_result is not None:
            return cached_result

        has_access = self.hospital_memberships_user.filter(
            tenant__schema_name=schema_name
        ).exists()
        print(has_access)

        cache.set(cache_key, has_access, 300)  # Cache for 5 minutes
        return has_access

    def get_tenant_role(self, schema_name):
        """Get user's role in a specific tenant (with caching)."""
        cache_key = f"tenant_role_{self.id}_{schema_name}"
        cached_role = cache.get(cache_key)

        if cached_role is not None:
            return cached_role

        try:
            membership = self.hospital_memberships_user.get(
                tenant__schema_name=schema_name
            )
            cache.set(cache_key, membership.role, 300)
            return membership.role
        except HospitalMembership.DoesNotExist:
            return None

    def get_tenant_permissions(self, schema_name):
        """Get all permissions for a specific tenant."""
        cache_key = f"tenant_perms_{self.id}_{schema_name}"
        cached_perms = cache.get(cache_key)

        if cached_perms is not None:
            return cached_perms

        try:
            membership = self.hospital_memberships_user.get(
                tenant__schema_name=schema_name
            )
            perms = set()

            # Get permissions from groups
            for group in membership.role.groups.all():
                perms.update(group.permissions.values_list("codename", flat=True))

            cache.set(cache_key, perms, 300)
            return perms

        except HospitalMembership.DoesNotExist:
            return set()

    def has_perm(self, perm, obj=None):
        """Override default permission check with tenant context."""
        if self.is_superuser:
            return True

        # Get tenant schema from current connection
        tenant_schema = connection.schema_name

        if tenant_schema == "public":
            return super().has_perm(perm, obj)

        return perm in self.get_tenant_permissions(tenant_schema)

    def is_patient(self):
        return self.hospital_memberships.filter(role="Patient").exists()

    def is_staff_member(self):
        return self.hospital_memberships.filter(role__in=["Doctor", "Durse", "Admin", "Tenant Admin"]).exists()
