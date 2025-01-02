from rest_framework.permissions import BasePermission

# from django.contrib.auth.models import Permission
from apps.staff.helper import convert_queryset_to_role_permissions
from apps.staff.models import StaffRole

ROLE_PERMISSIONS = {
    "DOCTOR": {
        "patient": ["view", "add", "change"],
        "patientdemographics": ["view", "add", "change"],
        "patientaddress": ["view"],
    },
    "HEAD_DOCTOR": {
        "patient": ["view", "add", "change", "delete"],
        "patientdemographics": ["view", "add", "change", "delete"],
        "patientaddress": ["view", "add", "delete"],
    },
    "NURSE": {
        "patient": ["view"],
        "patientdemographics": ["view", "add", "change"],
        "patientaddress": ["view"],
    },
    "HEAD_NURSE": {
        "patient": ["view", "add"],
        "patientdemographics": ["view", "add", "change", "delete"],
        "patientaddress": ["view"],
    },
    "RECEPTIONIST": {
        "patient": ["view", "add"],
        "patientdemographics": ["view"],
        "patientaddress": ["view", "add", "change"],
    },
    "LAB_TECHNICIAN": {
        "patient": ["view"],
        "patientdemographics": ["view"],
    },
    "PHARMACIST": {
        "patient": ["view"],
        "patientdemographics": ["view"],
    },
}


class RolePermission(BasePermission):
    """
    Custom permission to check user roles and their permissions.
    """

    def __init__(self):
        super().__init__()
        # print("RolePermission initialized")

    def has_permission(self, request, view):
        # Extract and normalize the user role
        raw_role = getattr(request.user, "role", None)
        if not raw_role:
            return False

        # Extract role as string
        user_role = str(raw_role).strip().upper().replace(" ", "_")
        # print(f"Extracted and normalized user role: {user_role}")

        # Check if role is in ROLE_PERMISSIONS
        if user_role not in ROLE_PERMISSIONS:
            # print(f"Role '{user_role}' not in defined permissions.")
            # print(f"Available roles: {ROLE_PERMISSIONS.keys()}")
            return False

        # Determine resource and action
        resource = view.basename  # Normalize resource name
        resource_ = resource.replace("-", " ")  # Replace hyphens with spaces
        normalized_resource = "".join(word for word in resource_.split()) 
        action = view.action
        
        # Map DRF actions to permissions
        action_to_permission = {
            "list": "view",
            "retrieve": "view",
            "create": "add",
            "update": "change",
            "partial_update": "change",
            "destroy": "delete",
        }
        permission = action_to_permission.get(action)
        if not permission:
            return False

       
        # Check if the user's role has the required permission
        allowed_permissions = ROLE_PERMISSIONS.get(user_role, {})
        inner_lists = allowed_permissions.get(normalized_resource)
        if permission in inner_lists:
            return True
        return False

class PermissionCheckedSerializerMixin:
    """
    A mixin to handle permission checking in serializers with support for both
    QuerySet and dictionary-based permissions.
    """
    def check_permission(self, permission_type: str, model_name: str) -> bool:
        request = self.context.get('request')
        if not request or not request.user:
            return False
        
        user_role = request.user.role
        role = str(user_role).strip().upper().replace(" ", "_")
        
        
        # If using the database permissions
        if hasattr(request.user, 'user_permissions'):
            perms = StaffRole.objects.get(code=role).permissions.all()
            permissions_dict = convert_queryset_to_role_permissions(perms)
            model_permissions = permissions_dict.get(model_name, [])
        else:
            # Fall back to ROLE_PERMISSIONS dictionary
            user_permissions = ROLE_PERMISSIONS.get(role, {})
            model_permissions = user_permissions.get(model_name, [])
            
        return permission_type in model_permissions