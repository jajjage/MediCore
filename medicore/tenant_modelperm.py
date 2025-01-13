from django.contrib.auth.backends import BaseBackend
from django.contrib.contenttypes.models import ContentType
from django.db import connection


class TenantModelPermissionBackend(BaseBackend):
    def has_perm(self, user_obj, perm, obj=None):
        if not user_obj.is_active:
            return False

        # Admin users have all permissions
        if user_obj.get_tenant_permission_type(connection.schema_name) == "ADMIN":
            return True

        # Parse the permission string (e.g., "staff.view_department")
        try:
            app_label, perm_name = perm.split(".")
            action, model_name = perm_name.split("_")
            print(action, model_name)
        except ValueError:
            return False

        # Get the model's content type
        try:
            content_type = ContentType.objects.get(
                app_label=app_label,
                model=model_name
            )
        except ContentType.DoesNotExist:
            return False

        # Check if user has the specific model permission
        return user_obj.tenant_permissions.filter(
            schema_name=connection.schema_name,
            model_permissions__content_type=content_type,
            model_permissions__permission_type=action
        ).exists()
