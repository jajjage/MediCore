import uuid

from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    Group,
    PermissionsMixin,
)
from django.core.cache import cache
from django.db import connection, models


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


    def clear_permission_cache(self):
        """Clear all cached permissions for this user."""
        keys = [
            f"user_perms_{self.id}_*",
            f"tenant_access_{self.id}_*",
            f"tenant_role_{self.id}_*",
        ]
        for key in keys:
            cache.delete_pattern(key)

    def has_tenant_access(self, tenant_schema):
        """Check if user has access to a specific tenant (with caching)."""
        cache_key = f"tenant_access_{self.id}_{tenant_schema}"
        cached_result = cache.get(cache_key)

        if cached_result is not None:
            return cached_result

        has_access = self.tenant_memberships.filter(
            tenant__schema_name=tenant_schema
        ).exists()

        cache.set(cache_key, has_access, 300)  # Cache for 5 minutes
        return has_access

    def get_tenant_role(self, tenant_schema):
        """Get user's role in a specific tenant (with caching)."""
        cache_key = f"tenant_role_{self.id}_{tenant_schema}"
        cached_role = cache.get(cache_key)

        if cached_role is not None:
            return cached_role

        try:
            membership = self.tenant_memberships.get(
                tenant__schema_name=tenant_schema
            )
            cache.set(cache_key, membership.role, 300)
            return membership.role
        except TenantMemberships.DoesNotExist:
            return None

    def get_tenant_permissions(self, tenant_schema):
        """Get all permissions for a specific tenant."""
        cache_key = f"tenant_perms_{self.id}_{tenant_schema}"
        cached_perms = cache.get(cache_key)

        if cached_perms is not None:
            return cached_perms

        try:
            membership = self.tenant_memberships.get(
                tenant__schema_name=tenant_schema
            )
            perms = set()

            # Get permissions from groups
            for group in membership.groups.all():
                perms.update(group.permissions.values_list("codename", flat=True))

            cache.set(cache_key, perms, 300)
            return perms

        except TenantMemberships.DoesNotExist:
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
