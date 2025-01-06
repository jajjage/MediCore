import uuid

from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.db import connection, models


class MyUserManager(BaseUserManager):
    def create_tenant_admin(self, email, hospital, password=None):
        """
        Handle Creates and saves a tenant admin user.
        """
        if not email:
            raise ValueError("Users must have an email address")
        if not hospital:
            raise ValueError("Tenant admin must be associated with a hospital")

        user = self.model(
            email=self.normalize_email(email), hospital=hospital, is_tenant_admin=True
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None):
        """
        Handle Creates and saves a superuser.
        """
        user = self.model(
            email=self.normalize_email(email), is_superuser=True, is_tenant_admin=True
        )
        user.set_password(password)
        user.save(using=self._db)
        return user


class MyUser(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    hospital = models.ForeignKey(
        "tenants.Client", on_delete=models.CASCADE, null=True, blank=True
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=True)
    is_tenant_admin = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    groups = models.ManyToManyField(
        "auth.Group",
        related_name="myuser_set",
        blank=True,
        verbose_name="groups",
        help_text="The groups this user belongs to.",
    )
    user_permissions = models.ManyToManyField(
        "auth.Permission",
        related_name="myuser_set",
        blank=True,
        verbose_name="user permissions",
        help_text="Specific permissions for this user.",
    )

    objects = MyUserManager()

    USERNAME_FIELD = "email"

    class Meta:
        db_table = "core_user"

    def has_perm(self, perm, obj=None):
        if connection.schema_name == "public":
            if self.is_superuser:
                # Only allow permissions for shared apps
                app_label = perm.split(".")[0]
                return app_label in ["auth", "core", "tenants"]
            return False
        # In tenant schema, tenant admin has full permissions
        return self.is_tenant_admin

    def has_module_perms(self, app_label):
        if connection.schema_name == "public":
            if self.is_superuser:
                # Only show shared apps in admin
                return app_label in ["auth", "core", "tenants"]
            return False
        # In tenant schema, tenant admin can see all tenant apps
        if self.is_tenant_admin:
            return app_label not in ["auth", "core", "tenants"]
        return False
