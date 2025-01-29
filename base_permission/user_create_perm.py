from django.core.cache import cache
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission

from apps.staff.helper import (
    convert_queryset_to_role_permissions,
)
from hospital.models import Role

ROLE_PERMISSIONS = {
            "SUPERUSER": {
                "name": "Superuser",
                "description": "Has all permissions in the system",
                "permissions": {
                    "myuser": ["view", "add", "change", "delete"],
                    "role": ["view", "add", "change", "delete"],
                    "hospitalprofile": ["view", "add", "change", "delete"],
                    "hospitalmembership": ["view", "add", "change", "delete"],
                    "client": ["view", "add", "change", "delete"],
                    "domain": ["view", "add", "change", "delete"],
                },
            },
            "TENANT_ADMIN": {
                "name": "Tenant Admin",
                "description": "Has all permissions in the tenant",
                "permissions": {
                    "patient": ["view", "add", "change", "delete"],
                    "patientdemographics": ["view", "add", "change", "delete"],
                    "patientemergencycontact": ["view", "add", "change", "delete"],
                    "patientallergies": ["view", "add", "change", "delete"],
                    "patientchroniccondition": ["view", "add", "change", "delete"],
                    "patientmedicalreport": ["view", "add", "change", "delete"],
                    "patientvisit": ["view", "add", "change", "delete"],
                    "patientappointment": ["view", "add", "change", "delete"],
                    "patientdiagnoses": ["view", "add", "change", "delete"],
                    "patientoperation": ["view", "add", "change", "delete"],
                    "patientprescription": ["view", "add", "change", "delete"],
                    "department": ["view", "add", "change", "delete"],
                    "departmentmember": ["view", "add", "change", "delete"],
                    "shiftpattern": ["view", "add", "change", "delete"],
                    "stafftransfer": ["view", "add", "change", "delete"],
                    "workloadassignment": ["view", "add", "change", "delete"],
                    "doctorprofile": ["view", "add", "change", "delete"],
                    "nurseprofile": ["view", "add", "change", "delete"],
                    "technicianprofile": ["view", "add", "change", "delete"],

                },
            },
            "DOCTOR": {
                "name": "Doctor",
                "description": "Medical Doctor with patient care responsibilities",
                "permissions": {
                    "patient": ["view", "add", "change"],
                    "patientallergies": ["view", "add", "change"],
                    "patientappointment": ["view", "add", "change"],
                    "patientchroniccondition": ["view", "add", "change"],
                    "patientdemographics": ["view", "add", "change"],
                    "patientdiagnoses": ["view", "add", "change"],
                    "patientemergencycontact": ["view"],
                    "patientmedicalreport": ["view", "add", "change"],
                    "patientoperation": ["view", "add", "change"],
                    "patientvisit": ["view", "add", "change"],
                    "patientprescription": ["view", "add", "change"],
                },
            },
            "HEAD_DOCTOR": {
                "name": "Head Doctor",
                "description": "Senior medical doctor with additional permissions",
                "permissions": {
                    "patient": ["view", "add", "change", "delete"],
                    "patientallergies": ["view", "add", "change", "delete"],
                    "patientappointment": ["view", "add", "change", "delete"],
                    "patientchroniccondition": ["view", "add", "change", "delete"],
                    "patientdemographics": ["view", "add", "change", "delete"],
                    "patientdiagnoses": ["view", "add", "change", "delete"],
                    "patientemergencycontact": ["view", "add", "change", "delete"],
                    "patientmedicalreport": ["view", "add", "change", "delete"],
                    "patientoperation": ["view", "add", "change", "delete"],
                    "patientvisit": ["view", "add", "change", "delete"],
                    "patientprescription": ["view", "add", "change"],
                },
            },
            "NURSE": {
                "name": "Nurse",
                "description": "Nursing staff providing patient support",
                "permissions": {
                    "patient": ["view"],
                    "patientallergies": ["view", "add"],
                    "patientappointment": ["view", "add"],
                    "patientchroniccondition": ["view"],
                    "patientdemographics": ["view", "add"],
                    "patientdiagnoses": ["view"],
                    "patientemergencycontact": ["view"],
                    "patientmedicalreport": ["view"],
                    "patientoperation": ["view"],
                    "patientvisit": ["view", "add", "change"],
                },
            },
            "LAB_TECH": {
                "name": "Lab Technician",
                "code": "LAB_TECH",
                "description": "Handles laboratory tests and procedures",
                "permissions": {
                    "patient": ["view"],
                    "patientallergies": ["view"],
                    "patientappointment": ["view"],
                    "patientchroniccondition": ["view"],
                    "patientdemographics": ["view"],
                    "patientdiagnoses": ["view"],
                    "patientemergencycontact": ["view"],
                    "patientmedicalreport": ["view", "add", "change"],
                    "patientoperation": ["view"],
                    "patientvisit": ["view", "add", "change"],
                },
            },
            "PATIENT": {
                "name": "Patient",
                "description": "Patient access to own records",
                "permissions": {
                    "patient": ["view"],
                    "patientdemographics": ["view"],
                    "patientemergencycontact": ["view"],
                    "patientallergies": ["view"],
                    "patientchroniccondition": ["view"],
                    "patientmedicalreport": ["view"],
                    "patientvisit": ["view"],
                    "patientappointment": ["view"],
                    "patientdiagnoses": ["view"],
                    "patientoperation": ["view"],
                    "patientprescription": ["view"],
                },
            }
        }


class UserCreatePermission(BasePermission):
    """
    Custom permission to check user roles and their permissions.
    """

    def __init__(self):
        super().__init__()

    def has_permission(self, request, view):
        # Extract and normalize the user role
        try:
            user_role = request.user.hospital_memberships_user.first().role
            if not user_role:
                return False

            user_role = str(user_role).strip()

            if user_role not in ROLE_PERMISSIONS:
                return False

            if not hasattr(view, "basename"):
                return False

            resource = view.basename
            resource_ = resource.replace("-", " ")
            normalized_resource = "".join(word for word in resource_.split())

            permission = "add"
            cache_key = f"user_role_permissions_create{user_role}"
            # Check cache first
            permissions = cache.get(cache_key)
            try:
                role = Role.objects.get(code=user_role)
            except Role.DoesNotExist as err:
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
        except AttributeError:
            raise PermissionDenied("User does not have a valid hospital membership role.")
        except (ValueError, Role.DoesNotExist) as e:
            raise PermissionDenied(f"Error: {e}")
