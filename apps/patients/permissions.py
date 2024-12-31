# permissions.py
from rest_framework import permissions
from functools import wraps
from rest_framework.exceptions import PermissionDenied

class StaffPermission(permissions.BasePermission):
    """
    Base permission class for HMS staff members using StaffRole
    """
    allowed_roles = []  # Role codes to be defined in StaffRole model
    required_permissions = {}  # Map HTTP methods to required permissions

    def has_permission(self, request, view):
        # Check if user is authenticated
        if not request.user or not request.user.is_authenticated:
            return False
            
        # Superuser has all permissions
        if request.user.is_superuser:
            return True

        # Get user role from StaffMember
        user_role = request.user.role.code if hasattr(request.user, 'role') else None
        
        # Check if user has required role
        if not user_role or user_role not in self.allowed_roles:
            return False

        # Check method-specific permissions
        method = request.method
        if method in self.required_permissions:
            required_perms = self.required_permissions[method]
            return request.user.has_perms(required_perms)

        return True

class DoctorPermission(StaffPermission):
    allowed_roles = ['DOCTOR', 'HEAD_DOCTOR']  # Role codes from StaffRole
    required_permissions = {
        'GET': ['hms.view_patient', 'hms.view_patient_demographics'],
        'POST': ['hms.add_patient', 'hms.change_patient_demographics'],
        'PUT': ['hms.change_patient', 'hms.change_patient_demographics'],
        'DELETE': ['hms.delete_patient']
    }

class NursePermission(StaffPermission):
    allowed_roles = ['NURSE', 'HEAD_NURSE']
    required_permissions = {
        'GET': ['hms.view_patient', 'hms.view_patient_demographics'],
        'POST': ['hms.add_patient_demographics'],
        'PUT': ['hms.change_patient_demographics'],
        'DELETE': []
    }

class ReceptionistPermission(StaffPermission):
    allowed_roles = ['RECEPTIONIST']
    required_permissions = {
        'GET': ['hms.view_patient'],
        'POST': ['hms.add_patient', 'hms.add_patient_address'],
        'PUT': ['hms.change_patient_address'],
        'DELETE': []
    }



def require_staff_role(role_codes):
    """
    Decorator to check staff role codes
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(view_instance, request, *args, **kwargs):
            user_role = request.user.role.code if hasattr(request.user, 'role') else None
            if user_role not in role_codes and not request.user.is_superuser:
                raise PermissionDenied("You do not have permission to perform this action.")
            return view_func(view_instance, request, *args, **kwargs)
        return wrapped_view
    return decorator