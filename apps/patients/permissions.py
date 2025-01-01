from rest_framework.permissions import BasePermission

ROLE_PERMISSIONS = {
    "DOCTOR": {
        "patient": ["view", "add", "change"],
        "patientdemographics": ["view", "add", "change"],
        "patientaddress": ["view"],
    },
    "HEAD_DOCTOR": {
        "patient": ["view", "add", "change", "delete"],
        "patientdemographics": ["view", "add", "change", "delete"],
        "patientaddress": ["view", "delete"],
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
        print("RolePermission initialized")

    def has_permission(self, request, view):
        # Extract and normalize the user role
        raw_role = getattr(request.user, "role", None)
        if not raw_role:
            print("User role is not set.")
            return False

        # Extract role as string
        user_role = str(raw_role).strip().upper().replace(" ", "_")
        print(f"Extracted and normalized user role: {user_role}")

        # Check if role is in ROLE_PERMISSIONS
        if user_role not in ROLE_PERMISSIONS:
            print(f"Role '{user_role}' not in defined permissions.")
            print(f"Available roles: {ROLE_PERMISSIONS.keys()}")
            return False

        # Determine resource and action
        resource = view.basename.rstrip("s")  # Normalize resource name
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
            # print(f"Action '{action}' is not defined in action_to_permission.")
            return False

        # print(f"Permission needed: {permission}")

        # Check if the user's role has the required permission
        allowed_permissions = ROLE_PERMISSIONS.get(user_role, {}).get(resource, [])
        if permission in allowed_permissions:
            # print(f"Permission granted for {user_role} to {action} {resource}.")
            return True

        # print(f"Permission denied for {user_role} to {action} {resource}.")
        return False
