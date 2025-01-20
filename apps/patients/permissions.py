from django.core.cache import cache
from rest_framework.permissions import BasePermission

from apps.staff.helper import (
    convert_queryset_to_role_permissions,
    normalize_permissions_dict,
)
from apps.staff.models import StaffRole

ROLE_PERMISSIONS = {
    "DOCTOR": {
        "name": "Doctor",
        "permissions": {
            "patient": ["view", "add", "change"],
            "patientaddress": ["view"],
            "patientallergy": ["view", "add", "change"],
            "patientappointment": ["view", "add", "change"],
            "patientchroniccondition": ["view", "add", "change"],
            "patientdemographics": ["view", "add", "change"],
            "patientdiagnosis": ["view", "add", "change"],
            "patientemergencycontact": ["view"],
            "patientmedicalreport": ["view", "add", "change"],
            "patientoperation": ["view", "add", "change"],
            "patientvisit": ["view", "add", "change"],
        },
    },
    "HEAD_DOCTOR": {
        "name": "Head Doctor",
        "permissions": {
            "patient": ["view", "add", "change", "delete"],
            "patientaddress": ["view", "add", "change", "delete"],
            "patientallergy": ["view", "add", "change", "delete"],
            "patientappointment": ["view", "add", "change", "delete"],
            "patientchroniccondition": ["view", "add", "change", "delete"],
            "patientdemographics": ["view", "add", "change", "delete"],
            "patientdiagnosis": ["view", "add", "change", "delete"],
            "patientemergencycontact": ["view", "add", "change", "delete"],
            "patientmedicalreport": ["view", "add", "change", "delete"],
            "patientoperation": ["view", "add", "change", "delete"],
            "patientvisit": ["view", "add", "change", "delete"],
        },
    },
    "NURSE": {
        "name": "Nurse",
        "permissions": {
            "patient": ["view"],
            "patientaddress": ["view"],
            "patientallergy": ["view", "add"],
            "patientappointment": ["view", "add"],
            "patientchroniccondition": ["view"],
            "patientdemographics": ["view", "add"],
            "patientdiagnosis": ["view"],
            "patientemergencycontact": ["view"],
            "patientmedicalreport": ["view"],
            "patientoperation": ["view"],
            "patientvisit": ["view", "add", "change"],
        },
    },
    "LAB_TECHNICIAN": {
        "name": "Lab Technician",
        "permissions": {
            "patient": ["view"],
            "patientaddress": ["view"],
            "patientallergy": ["view"],
            "patientappointment": ["view"],
            "patientchroniccondition": ["view"],
            "patientdemographics": ["view"],
            "patientdiagnosis": ["view"],
            "patientemergencycontact": ["view"],
            "patientmedicalreport": ["view", "add", "change"],
            "patientoperation": ["view"],
            "patientvisit": ["view", "add", "change"],
        },
    },
    "PHARMACIST": {
        "name": "Pharmacist",
        "permissions": {
            "patient": ["view"],
            "patientaddress": ["view"],
            "patientallergy": ["view"],
            "patientappointment": ["view"],
            "patientchroniccondition": ["view"],
            "patientdemographics": ["view"],
            "patientdiagnosis": ["view"],
            "patientemergencycontact": ["view"],
            "patientmedicalreport": ["view"],
            "patientoperation": ["view"],
            "patientvisit": ["view", "add", "change"],
        },
    },
}


class RolePermission(BasePermission):
    """
    Custom permission to check user roles and their permissions.
    """

    def __init__(self):
        super().__init__()

    def has_permission(self, request, view):
        # Extract and normalize the user role
        raw_role = getattr(request.user, "role", None)
        if not raw_role:
            return False

        # Extract role as string
        user_role = str(raw_role).strip().upper().replace(" ", "_")


        if user_role not in ROLE_PERMISSIONS:
            return False

        if not hasattr(view, "basename") or not hasattr(view, "action"):
            return False

        resource = view.basename
        resource_ = resource.replace("-", " ")
        normalized_resource = "".join(word for word in resource_.split())
        action = view.action
        print(f"Action received: {action}")
        print(normalized_resource)


        # Map DRF actions to permissions
        action_to_permission = {
            "list": "view",
            "retrieve": "view",
            "create": "add",
            "update": "change",
            "partial_update": "change",
            "destroy": "delete",
            "search": "view",
            "update_emergency_contact": "add",
            # Add any custom actions here
            "cancel": "change",
            "reschedule": "change",
            "update_status": "change",
            "available_slots": "view",
            "check_availability": "add",
            "create_recurring": "add"
        }
        permission = action_to_permission.get(action)
        print(f"Resolved permission for action '{action}': {permission}")

        if not permission:
            return False
        cache_key = f"user_role_permissions_{user_role}"
        # Check cache first
        permissions = cache.get(cache_key)
        try:
            role = StaffRole.objects.get(code=user_role)
        except StaffRole.DoesNotExist as err:
            raise ValueError(
                f"No StaffRole found with code: normalize_role: {user_role}"
            ) from err
        if permissions is None:
            permissions_queryset = role.permissions.all()
            # Convert to desired structure
            permissions_dict = convert_queryset_to_role_permissions(
                permissions_queryset
            )
            # Cache the permissions for 1 hour
            cache.set(cache_key, permissions_dict, timeout=3600)
            permissions = permissions_dict

        # Check if the user's role has the required permission
        model_permissions = permissions.get(normalized_resource, [])
        if not model_permissions:
            allowed_permissions = ROLE_PERMISSIONS.get(user_role, {}).get(
                "permissions", {}
            )
            model_permissions = allowed_permissions.get(normalized_resource, [])

        return permission in model_permissions


class PermissionCheckedSerializerMixin:
    def check_permission(self, permission_type: str, model_name: str) -> bool:
        request = self.context.get("request")
        if not request or not request.user:
            return False

        user_role = request.user.role
        normalize_role = str(user_role).strip().upper().replace(" ", "_")


        cache_key = f"user_role_permissions_{user_role}"
        permissions = cache.get(cache_key)

        try:
            role = StaffRole.objects.get(code=normalize_role)
            print(f"Found role: {role}")
        except StaffRole.DoesNotExist as err:
            print(f"Role not found: {normalize_role}")
            raise ValueError(
                f"No StaffRole found with code: normalize_role: {normalize_role}"
            ) from err

        if permissions is None:
            permissions_queryset = role.permissions.all()
            permissions_dict = convert_queryset_to_role_permissions(
                permissions_queryset
            )
            cache.set(cache_key, permissions_dict, timeout=36)
            permissions = permissions_dict

        if hasattr(request.user, "user_permissions"):
            model_permissions = permissions.get(model_name, [])
        else:
            user_permissions = ROLE_PERMISSIONS.get(normalize_role, {})
            permissions_dict = normalize_permissions_dict(user_permissions)
            model_permissions = permissions_dict.get(model_name, [])

        result = permission_type in model_permissions
        return result
