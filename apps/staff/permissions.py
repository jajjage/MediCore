from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from rest_framework.permissions import BasePermission
from rest_framework.viewsets import ViewSet


class TenantModelPermission(BasePermission):
    """
    Custom permission to check user permissions based on tenant and model level.

    Handles both ViewSets and APIViews.
    """

    def get_permission_type(self, view):
        """
        Determine the permission type based on view type and HTTP method.
        """
        # Handle ViewSets
        if isinstance(view, ViewSet):
            # Map common viewset actions to permission types
            action_to_permission = {
                "list": "view",
                "retrieve": "view",
                "create": "add",
                "update": "change",
                "partial_update": "change",
                "destroy": "delete"
            }
            return action_to_permission.get(view.action, view.action)

        # Handle regular APIViews
        method_to_permission = {
            "GET": "view",
            "POST": "add",
            "PUT": "change",
            "PATCH": "change",
            "DELETE": "delete"
        }
        return method_to_permission.get(view.request.method, None)

    def get_model_class(self, view):
        """
        Extract the model class from the view.
        """
        # Try getting model from queryset
        if hasattr(view, "queryset"):
            return view.queryset.model
        # Try getting model from serializer
        if hasattr(view, "get_serializer_class"):
            serializer_class = view.get_serializer_class()
            if hasattr(serializer_class, "Meta"):
                return serializer_class.Meta.model
        return None

    def has_permission(self, request, view):
        # Get and validate required data
        schema_name = request.tenant.schema_name if hasattr(request, "tenant") else None
        model_class = self.get_model_class(view)
        permission_type = self.get_permission_type(view)

        if not all([schema_name, model_class, permission_type]):
            return False

        # Check cache first
        cache_key = f"tenant_model_perm_{request.user.id}_{schema_name}_{model_class._meta.model_name}"
        cached_permissions = cache.get(cache_key)

        if cached_permissions is None:
            # Get content type for the model
            content_type = ContentType.objects.get_for_model(model_class)

            try:
                # Get tenant permission
                tenant_perm = request.user.tenant_permissions.get(schema_name=schema_name)

                # Get all model permissions for this content type
                model_permissions = tenant_perm.model_permissions.filter(
                    content_type=content_type
                ).values_list("permission_type", flat=True)

                # Cache the permissions
                cache.set(cache_key, list(model_permissions), timeout=3600)
                cached_permissions = model_permissions

            except request.user.tenant_permissions.model.DoesNotExist:
                cache.set(cache_key, [], timeout=3600)
                return False

        # Check if user has required permission
        if permission_type in cached_permissions:
            return True

        # If user has ADMIN permission type at tenant level, grant all permissions
        try:
            tenant_perm = request.user.tenant_permissions.get(schema_name=schema_name)
            return tenant_perm.permission_type == "ADMIN"
        except request.user.tenant_permissions.model.DoesNotExist:
            return False