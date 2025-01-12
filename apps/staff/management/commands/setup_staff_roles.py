from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db import connection

from apps.patients.models import (
    Patient,
    PatientAddress,
    PatientAllergies,
    PatientAppointment,
    PatientChronicConditions,
    PatientDemographics,
    PatientDiagnosis,
    PatientEmergencyContact,
    PatientMedicalReport,
    PatientOperation,
    PatientPrescription,
    PatientVisit,
)
from apps.staff.models import StaffRole


class Command(BaseCommand):
    help = "Setup staff roles and their permissions for the current schema"

    def handle(self, *args, **kwargs):
        # Get the current schema from the connection
        current_schema = connection.schema_name
        self.stdout.write(f"Starting staff roles setup for current schema: {current_schema}")

        # Define all roles and their permissions
        roles_data = {
            "DOCTOR": {
                "name": "Doctor",
                "permissions": {
                    "patient": ["view", "add", "change"],
                    "patientaddress": ["view"],
                    "patientallergies": ["view", "add", "change"],
                    "patientappointment": ["view", "add", "change"],
                    "patientchronicconditions": ["view", "add", "change"],
                    "patientdemographics": ["view", "add", "change"],
                    "patientdiagnosis": ["view", "add", "change"],
                    "patientemergencycontact": ["view"],
                    "patientmedicalreport": ["view", "add", "change"],
                    "patientoperation": ["view", "add", "change"],
                    "patientvisit": ["view", "add", "change"],
                    "patientprescription": ["view", "add", "change"],
                },
            },
            "HEAD_DOCTOR": {
                "name": "Head Doctor",
                "permissions": {
                    "patient": ["view", "add", "change", "delete"],
                    "patientaddress": ["view", "add", "change", "delete"],
                    "patientallergies": ["view", "add", "change", "delete"],
                    "patientappointment": ["view", "add", "change", "delete"],
                    "patientchronicconditions": ["view", "add", "change", "delete"],
                    "patientdemographics": ["view", "add", "change", "delete"],
                    "patientdiagnosis": ["view", "add", "change", "delete"],
                    "patientemergencycontact": ["view", "add", "change", "delete"],
                    "patientmedicalreport": ["view", "add", "change", "delete"],
                    "patientoperation": ["view", "add", "change", "delete"],
                    "patientvisit": ["view", "add", "change", "delete"],
                    "patientprescription": ["view", "add", "change"],
                },
            },
            "NURSE": {
                "name": "Nurse",
                "permissions": {
                    "patient": ["view"],
                    "patientaddress": ["view"],
                    "patientallergies": ["view", "add"],
                    "patientappointment": ["view", "add"],
                    "patientchronicconditions": ["view"],
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
                    "patientallergies": ["view"],
                    "patientappointment": ["view"],
                    "patientchronicconditions": ["view"],
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
                    "patientallergies": ["view"],
                    "patientappointment": ["view"],
                    "patientchronicconditions": ["view"],
                    "patientdemographics": ["view"],
                    "patientdiagnosis": ["view"],
                    "patientemergencycontact": ["view"],
                    "patientmedicalreport": ["view"],
                    "patientoperation": ["view"],
                    "patientvisit": ["view", "add", "change"],
                },
            },
        }

        try:
            with connection.cursor() as cursor:
                self.setup_roles(roles_data)

                # Create sequences
                cursor.execute("""
                    CREATE SEQUENCE IF NOT EXISTS patient_pin_seq_middle
                    START WITH 20
                    INCREMENT BY 1
                    MINVALUE 20
                    MAXVALUE 99999
                    CYCLE;
                """)
                cursor.execute("""
                    CREATE SEQUENCE IF NOT EXISTS patient_pin_seq_last
                    START WITH 40
                    INCREMENT BY 1
                    MINVALUE 40
                    MAXVALUE 99999
                    CYCLE;
                """)
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS patient_pin_lower_idx ON patients (LOWER(pin));"
                )

            self.stdout.write(
                self.style.SUCCESS(
                    f"Staff roles setup completed successfully for schema: {current_schema}"
                )
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error during staff roles setup: {e}")
            )
            raise

    def setup_roles(self, roles_data):
        # Get content types for our models
        model_content_types = {
            "patient": ContentType.objects.get_for_model(Patient),
            "patientdemographics": ContentType.objects.get_for_model(PatientDemographics),
            "patientaddress": ContentType.objects.get_for_model(PatientAddress),
            "patientemergencycontact": ContentType.objects.get_for_model(PatientEmergencyContact),
            "patientallergies": ContentType.objects.get_for_model(PatientAllergies),
            "patientchronicconditions": ContentType.objects.get_for_model(PatientChronicConditions),
            "patientmedicalreport": ContentType.objects.get_for_model(PatientMedicalReport),
            "patientvisit": ContentType.objects.get_for_model(PatientVisit),
            "patientappointment": ContentType.objects.get_for_model(PatientAppointment),
            "patientdiagnosis": ContentType.objects.get_for_model(PatientDiagnosis),
            "patientoperation": ContentType.objects.get_for_model(PatientOperation),
            "patientprescription": ContentType.objects.get_for_model(PatientPrescription),
        }

        for role_code, role_info in roles_data.items():
            self.stdout.write(f'Processing role: {role_info["name"]}')

            # Create or update each role
            role, created = StaffRole.objects.get_or_create(
                code=role_code, defaults={"name": role_info["name"]}
            )

            if not created:
                role.name = role_info["name"]
                role.save()
                self.stdout.write(f"Updated existing role: {role.name}")
            else:
                self.stdout.write(f"Created new role: {role.name}")

            # Clear existing permissions
            role.permissions.clear()

            # Add permissions for each model
            for model_name, actions in role_info["permissions"].items():
                content_type = model_content_types[model_name]
                for action in actions:
                    codename = f"{action}_{model_name}"
                    try:
                        permission = Permission.objects.get(
                            codename=codename, content_type=content_type
                        )
                        role.permissions.add(permission)
                        self.stdout.write(f"Added permission: {codename} to {role.name}")
                    except Permission.DoesNotExist:
                        self.stdout.write(
                            self.style.WARNING(f"Permission {codename} does not exist")
                        )
