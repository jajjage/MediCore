from django.apps import AppConfig
from django.db.models.signals import post_migrate
from django.dispatch import receiver

class StaffConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.staff"

    def ready(self):
        # Only connect the signal, don't call directly
        post_migrate.connect(self._create_roles, sender=self)
    
    def _create_roles(self, sender, **kwargs):
        from .permissions import create_default_roles_and_permissions
        create_default_roles_and_permissions()