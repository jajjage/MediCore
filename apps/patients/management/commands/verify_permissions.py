from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
User = get_user_model()

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        for user in User.objects.filter(role__isnull=False):
            print(f"User: {user.username}")
            print(f"Role: {user.role.code}")
            print(f"Permissions: {user.get_all_permissions()}\n")