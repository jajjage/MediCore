from django.db import connection
from django.conf import settings


class DynamicAuthModelMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if connection.schema_name == "public":
            settings.AUTH_USER_MODEL = settings.PUBLIC_SCHEMA_USER_MODEL
        else:
            settings.AUTH_USER_MODEL = settings.TENANT_SCHEMA_USER_MODEL
        return self.get_response(request)
