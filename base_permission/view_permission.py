from django.core.cache import cache
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission

from apps.staff.helper import (
    convert_queryset_to_role_permissions,
    normalize_permissions_dict,
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
                    "nurseavailability": ["view", "add", "change", "delete"],
                    "shifttemplate": ["view", "add", "change", "delete"],
                    "shiftgeneration": ["view", "add", "change", "delete"],
                    "usershiftpreference": ["view", "add", "change", "delete"],
                    "shiftswaprequest": ["view", "add", "change", "delete"],
                    "weekendshiftpolicy": ["view", "add", "change", "delete"],

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

class RolePermission(BasePermission):
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
                print(f"User role not found: {user_role}")
                return False
            act = hasattr(view, "basename")
            if not hasattr(view, "basename") or not hasattr(view, "action"):
                print(f"View does not have basename or action: {act}")
                return False

            resource = view.basename
            resource_ = resource.replace("-", " ")
            normalized_resource = "".join(word for word in resource_.split())
            action = view.action
            print(f"Resource: {normalized_resource}, Action: {action}")

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

            if not permission:
                return False
            cache_key = f"user_role_permissions_{user_role}"
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
            cache.clear()  # Clear cache delete later
            if not model_permissions:
                allowed_permissions = ROLE_PERMISSIONS.get(user_role, {}).get(
                    "permissions", {}
                )
                model_permissions = allowed_permissions.get(normalized_resource, [])

            return permission in model_permissions
        except AttributeError:
            raise PermissionDenied("Authentication credentials were not provided.")
        except (ValueError, Role.DoesNotExist) as e:
            raise PermissionDenied(f"Error: {e}")


class PermissionCheckedSerializerMixin:
    def check_permission(self, permission_type: str, model_name: str) -> bool:
        request = self.context.get("request")
        if not request or not request.user:
            return False
        try:
            user_role = request.user.hospital_memberships_user.first().role
            normalize_role = str(user_role).strip().upper().replace(" ", "_")


            cache_key = f"user_role_permissions_{user_role}"
            permissions = cache.get(cache_key)

            try:
                role = Role.objects.get(code=normalize_role)
                print(f"Found role: {role}")
            except Role.DoesNotExist as err:
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
        except AttributeError:
            raise PermissionDenied("Authentication credentials were not provided.")
        except (ValueError, Role.DoesNotExist) as e:
            raise PermissionDenied(f"Error: {e}")
