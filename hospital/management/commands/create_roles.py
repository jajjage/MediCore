from django.core.management.base import BaseCommand

from hospital.models import Role  # Replace 'your_app' with your app name


class Command(BaseCommand):
    help = "Creates default roles in the database"

    def handle(self, *args, **options):
        default_roles = [
            {
                "name": "Doctor",
                "code": "DOCTOR",
                "description": "Medical Doctor with patient care responsibilities"
            },
            {
                "name": "Nurse",
                "code": "NURSE",
                "description": "Nursing staff providing patient support"
            },
            {
                "name": "Administrator",
                "code": "ADMIN",
                "description": "Hospital system administrator"
            },
            {
                "name": "Lab Technician",
                "code": "LAB_TECH",
                "description": "Handles laboratory tests and procedures"
            }
        ]

        for role_data in default_roles:
            role, created = Role.objects.get_or_create(
                code=role_data["code"],
                defaults={
                    "name": role_data["name"],
                    "description": role_data.get("description", ""),
                    "is_active": True
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created role: {role.name}"))
            else:
                self.stdout.write(f'Role "{role.name}" already exists')
