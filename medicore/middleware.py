import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.db import connection
from django.shortcuts import redirect
from django.urls import reverse
from django_tenants.utils import get_public_schema_name, schema_context

logger = logging.getLogger(__name__)


class AdminAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/admin/"):
            user = request.user

            # If not authenticated, allow normal login flow
            if not user.is_authenticated:
                return self.get_response(request)

            current_schema = connection.schema_name

            if current_schema == get_public_schema_name():
                # On main domain
                if not user.is_superuser:
                    messages.error(
                        request, "Access denied. Please log in to your hospital domain."
                    )
                    logout(request)
                    return redirect(reverse("admin:login"))
            # On tenant domain
            elif not user.hospital or user.hospital.schema_name != current_schema:
                messages.error(
                    request,
                    "Access denied. Please log in to your assigned hospital domain.",
                )
                logout(request)
                return redirect(reverse("admin:login"))

        return self.get_response(request)


class DynamicAuthModelMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if connection.schema_name == "public":
            settings.AUTH_USER_MODEL = settings.PUBLIC_SCHEMA_USER_MODEL
        else:
            settings.AUTH_USER_MODEL = settings.TENANT_SCHEMA_USER_MODEL
        return self.get_response(request)

class PublicSchemaMiddleware:
    """
    Middleware to ensure the public schema is used when accessing.
    routes not associated with a specific tenant.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # If the request is for the root domain (no tenant subdomain)
        if request.get_host() == "medicore.local:8000":
            # Switch to the public schema
            with schema_context("public"):
                response = self.get_response(request)
                return response

        # For other routes, use the default tenant logic
        return self.get_response(request)
