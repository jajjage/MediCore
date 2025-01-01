from django.apps import AppConfig
from django.conf import settings
from django.db import connection


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
