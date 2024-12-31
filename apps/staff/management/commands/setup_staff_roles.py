# management/commands/setup_staff_roles.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from apps.patients.models import Patient, PatientDemographics, PatientAddress

from apps.staff.models import StaffRole

class Command(BaseCommand):
    help = 'Setup staff roles and their permissions'

    def handle(self, *args, **kwargs):
        self.stdout.write('Starting staff roles setup...')
        
        # Define all roles and their permissions
        roles_data = {
            'DOCTOR': {
                'name': 'Doctor',
                'permissions': {
                    'patient': ['view', 'add', 'change'],
                    'patientdemographics': ['view', 'add', 'change'],
                    'patientaddress': ['view'],
                },
            },
            'HEAD_DOCTOR': {
                'name': 'Head Doctor',
                'permissions': {
                    'patient': ['view', 'add', 'change', 'delete'],
                    'patientdemographics': ['view', 'add', 'change', 'delete'],
                    'patientaddress': ['view', 'delete'],
                },
            },
            'NURSE': {
                'name': 'Nurse',
                'permissions': {
                    'patient': ['view'],
                    'patientdemographics': ['view', 'add', 'change'],
                    'patientaddress': ['view'],
                },
            },
            'HEAD_NURSE': {
                'name': 'Head Nurse',
                'permissions': {
                    'patient': ['view', 'add'],
                    'patientdemographics': ['view', 'add', 'change', 'delete'],
                    'patientaddress': ['view'],
                },
            },
            'RECEPTIONIST': {
                'name': 'Receptionist',
                'permissions': {
                    'patient': ['view', 'add'],
                    'patientdemographics': ['view'],
                    'patientaddress': ['view', 'add', 'change'],
                },
            },
            'LAB_TECHNICIAN': {
                'name': 'Lab Technician',
                'permissions': {
                    'patient': ['view'],
                    'patientdemographics': ['view'],
                },
            },
            'PHARMACIST': {
                'name': 'Pharmacist',
                'permissions': {
                    'patient': ['view'],
                    'patientdemographics': ['view'],
                },
            },
        }

        try:
            # Get content types for our models
            model_content_types = {
                'patient': ContentType.objects.get_for_model(Patient),
                'patientdemographics': ContentType.objects.get_for_model(PatientDemographics),
                'patientaddress': ContentType.objects.get_for_model(PatientAddress),
            }

            # Create or update each role
            for role_code, role_info in roles_data.items():
                self.stdout.write(f'Processing role: {role_info["name"]}')
                
                role, created = StaffRole.objects.get_or_create(
                    code=role_code,
                    defaults={'name': role_info['name']}
                )
                
                if not created:
                    role.name = role_info['name']
                    role.save()
                    self.stdout.write(f'Updated existing role: {role.name}')
                else:
                    self.stdout.write(f'Created new role: {role.name}')

                # Clear existing permissions
                role.permissions.clear()

                # Add permissions for each model
                for model_name, actions in role_info['permissions'].items():
                    content_type = model_content_types[model_name]
                    for action in actions:
                        codename = f"{action}_{model_name}"
                        try:
                            permission = Permission.objects.get(
                                codename=codename,
                                content_type=content_type
                            )
                            role.permissions.add(permission)
                            self.stdout.write(f'Added permission: {codename} to {role.name}')
                        except Permission.DoesNotExist:
                            self.stdout.write(
                                self.style.WARNING(
                                    f'Permission {codename} does not exist'
                                )
                            )

            self.stdout.write(self.style.SUCCESS('Staff roles setup completed successfully'))
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error during staff roles setup: {str(e)}')
            )
            raise