from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand

from apps.patients.models import (
    Patient,
    PatientAllergies,
    PatientAppointment,
    PatientChronicCondition,
    PatientDemographics,
    PatientDiagnoses,
    PatientEmergencyContact,
    PatientMedicalReport,
    PatientOperation,
    PatientPrescription,
    PatientVisit,
)
from apps.staff.models import (
    Department,
    DepartmentMember,
    DoctorProfile,
    NurseProfile,
    ShiftPattern,
    StaffTransfer,
    TechnicianProfile,
    WorkloadAssignment,
)
from core.models import MyUser
from hospital.models import HospitalMembership, HospitalProfile, Role
from tenants.models import Client, Domain


class Command(BaseCommand):
    help = "Creates default hospital roles with specific permissions"

    def handle(self, *args, **options):
        roles_data = {
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
                    "myuser": ["view", "add"],
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
                    "patientdemographics": ["view"],
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

        # Get content types for models
        model_content_types = {
            "patient": ContentType.objects.get_for_model(Patient),
            "patientdemographics": ContentType.objects.get_for_model(PatientDemographics),
            "patientemergencycontact": ContentType.objects.get_for_model(PatientEmergencyContact),
            "patientallergies": ContentType.objects.get_for_model(PatientAllergies),
            "patientchroniccondition": ContentType.objects.get_for_model(PatientChronicCondition),
            "patientmedicalreport": ContentType.objects.get_for_model(PatientMedicalReport),
            "patientvisit": ContentType.objects.get_for_model(PatientVisit),
            "patientappointment": ContentType.objects.get_for_model(PatientAppointment),
            "patientdiagnoses": ContentType.objects.get_for_model(PatientDiagnoses),
            "patientoperation": ContentType.objects.get_for_model(PatientOperation),
            "patientprescription": ContentType.objects.get_for_model(PatientPrescription),
            "department": ContentType.objects.get_for_model(Department),
            "departmentmember": ContentType.objects.get_for_model(DepartmentMember),
            "shiftpattern": ContentType.objects.get_for_model(ShiftPattern),
            "stafftransfer": ContentType.objects.get_for_model(StaffTransfer),
            "workloadassignment": ContentType.objects.get_for_model(WorkloadAssignment),
            "doctorprofile": ContentType.objects.get_for_model(DoctorProfile),
            "nurseprofile": ContentType.objects.get_for_model(NurseProfile),
            "technicianprofile": ContentType.objects.get_for_model(TechnicianProfile),
            "hospitalprofile": ContentType.objects.get_for_model(HospitalProfile),
            "hospitalmembership": ContentType.objects.get_for_model(HospitalMembership),
            "role": ContentType.objects.get_for_model(Role),
            "client": ContentType.objects.get_for_model(Client),
            "domain": ContentType.objects.get_for_model(Domain),
            "myuser": ContentType.objects.get_for_model(MyUser),
        }

        for role_code, role_info in roles_data.items():
            self.stdout.write(f'\nProcessing role: {role_info["name"]}')

            # Create or update role
            role, created = Role.objects.update_or_create(
                code=role_code,
                defaults={
                    "name": role_info["name"],
                    "description": role_info["description"],
                    "is_active": True
                }
            )

            status_msg = "Created" if created else "Updated"
            self.stdout.write(self.style.SUCCESS(f"{status_msg} role: {role.name}"))

            # Clear existing permissions
            role.permissions.clear()

            # Add permissions for each model
            added_perms = 0
            for model_name, actions in role_info["permissions"].items():
                content_type = model_content_types[model_name]
                for action in actions:
                    codename = f"{action}_{model_name}"
                    try:
                        permission = Permission.objects.get(
                            codename=codename,
                            content_type=content_type
                        )
                        role.permissions.add(permission)
                        added_perms += 1
                    except Permission.DoesNotExist:
                        self.stdout.write(
                            self.style.WARNING(f"  Permission {codename} does not exist")
                        )

            self.stdout.write(
                self.style.SUCCESS(f"  Added {added_perms} permissions to {role.name}")
            )

        self.stdout.write("\n" + self.style.SUCCESS("Successfully created all roles!"))
