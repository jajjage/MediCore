# permissions_config.py
from django.contrib.contenttypes.models import ContentType

from apps.staff.models import Department, DepartmentMember
from core.models import ModelPermission


class PermissionDefaults:
    # Define default model permissions for each role
    ROLE_PERMISSIONS = {
        "ADMIN": {
            Department: ["view", "add", "change", "delete"],
            DepartmentMember: ["view", "add", "change", "delete"],
            # Add other models with their permissions
        },
        "STAFF": {
            Department: ["view", "add"],
            DepartmentMember: ["view", "add", "change"],
            # Add other models with their permissions
        },
        "VIEWER": {
            Department: ["view"],
            DepartmentMember: ["view"],
            # Add other models with their permissions
        }
    }

    @classmethod
    def get_model_permissions(cls, role, model):
        """Get permissions for a specific role and model."""
        return cls.ROLE_PERMISSIONS.get(role, {}).get(model, [])

    @classmethod
    def setup_role_permissions(cls, tenant_permission):
        """ASetup all permissions for a role."""
        role = tenant_permission.permission_type
        permissions_to_create = []

        for model, default_permissions in cls.ROLE_PERMISSIONS.get(role, {}).items():
            content_type = ContentType.objects.get_for_model(model)
            for action in default_permissions:
               permissions_to_create.extend([
                    ModelPermission(
                        tenant_permission=tenant_permission,
                        content_type=content_type,
                        permission_type=action
                    )
                ])

        if permissions_to_create:
            ModelPermission.objects.bulk_create(permissions_to_create)
