# permissions.py
from django.core.cache import cache
from rest_framework.permissions import BasePermission
from rest_framework.viewsets import ViewSet

from .helper import convert_queryset_to_role_permissions
from .models import StaffRole

# Define permissions mapping for appointments
APPOINTMENT_PERMISSIONS = {
    "DOCTOR": {
        "permissions": {
            "department": ["view"],
        }
    },
    "NURSE": {
        "permissions": {
            "department": ["view"],
        }
    },
    "RECEPTIONIST": {
        "permissions": {
            "department": ["view"],
        }
    },
    "ADMIN": {
        "permissions": {
            "department": ["view"],
        }
    }
}

class AppointmentRolePermission(BasePermission):
    """
    Custom permission to check user roles and their permissions.

    Handles both ViewSets and APIViews.
    """

    def get_permission_type(self, view):
        """
        Determine the permission type based on view type and HTTP method.
        """
        # Handle ViewSets
        if isinstance(view, ViewSet):
            return view.action

        # Handle regular APIViews
        method_to_action = {
            "GET": "view",
            "POST": "add",
            "PUT": "change",
            "PATCH": "change",
            "DELETE": "delete"
        }
        return method_to_action.get(view.request.method, None)

    def get_resource_name(self, view):
        """
        Get the resource name from view.
        """
        # For ViewSets
        if hasattr(view, "basename"):
            resource = view.basename
        # For APIViews
        elif hasattr(view, "name"):
            resource = view.name
        # Fallback to view name
        else:
            resource = view.__class__.__name__.replace("View", "").lower()

        resource_ = resource.replace("-", " ")
        return "".join(word for word in resource_.split())

    def has_permission(self, request, view):
        # Extract and normalize the user role
        raw_role = getattr(request.user, "role", None)
        if not raw_role:
            return False
        print(f"Raw Role: {raw_role}")
        # Extract role as string
        user_role = str(raw_role).strip().upper().replace(" ", "_")

        # if user_role not in APPOINTMENT_PERMISSIONS:
        #     return False

        # Get permission type based on view type and method
        permission = self.get_permission_type(view)
        print(f"Perm Type: {permission}")
        if not permission:
            return False

        # Get resource name
        normalized_resource = self.get_resource_name(view)
        print(normalized_resource)
        # Check cache for role permissions
        cache_key = f"appointment_role_permissions_{user_role}"
        permissions = cache.get(cache_key)

        if permissions is None:
            try:
                role = StaffRole.objects.get(code=user_role)
            except StaffRole.DoesNotExist as err:
                raise ValueError(
                    f"No StaffRole found with code: {user_role}"
                ) from err

            permissions_queryset = role.permissions.all()
            permissions_dict = convert_queryset_to_role_permissions(
                permissions_queryset
            )
            # Cache the permissions
            cache.set(cache_key, permissions_dict, timeout=3600)
            permissions = permissions_dict

        # Check permissions
        model_permissions = permissions.get(normalized_resource, [])
        if not model_permissions:
            allowed_permissions = APPOINTMENT_PERMISSIONS.get(user_role, {}).get(
                "permissions", {}
            )
            model_permissions = allowed_permissions.get(normalized_resource, [])

        return permission in model_permissions
