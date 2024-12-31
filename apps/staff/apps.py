from django.apps import AppConfig
from django.db.models.signals import post_migrate

class StaffConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.staff"

    def ready(self):
        
        post_migrate.connect(self.create_roles, sender=self)

    def create_roles(self, sender, **kwargs):
        from apps.staff.management.commands.setup_staff_roles import Command
        try:
            Command().handle()
        except Exception as e:
            print(f"Error during role creation: {e}")
