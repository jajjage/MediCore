# Helper functions for permission management
from django.contrib.contenttypes.models import ContentType

from core.models import ModelPermission, TenantPermission


def get_model_permissions(user, schema_name, model):
    """Get all permissions for a user on a specific model in a schema."""
    content_type = ContentType.objects.get_for_model(model)
    try:
        tenant_perm = user.tenant_permissions.get(schema_name=schema_name)
        return tenant_perm.model_permissions.filter(content_type=content_type)
    except TenantPermission.DoesNotExist:
        return ModelPermission.objects.none()

def add_model_permission(user, schema_name, model, permission_type):
    """Add a model permission for a user in a schema."""
    tenant_perm, _ = TenantPermission.objects.get_or_create(
        user=user,
        schema_name=schema_name,
        defaults={"permission_type": "STAFF"}
    )

    content_type = ContentType.objects.get_for_model(model)

    return ModelPermission.objects.get_or_create(
        tenant_permission=tenant_perm,
        content_type=content_type,
        permission_type=permission_type
    )

def remove_model_permission(user, schema_name, model, permission_type):
    """Remove a model permission for a user in a schema."""
    content_type = ContentType.objects.get_for_model(model)
    ModelPermission.objects.filter(
        tenant_permission__user=user,
        tenant_permission__schema_name=schema_name,
        content_type=content_type,
        permission_type=permission_type
    ).delete()
