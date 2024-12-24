# core/middleware.py
from django.contrib.auth import logout
from django.db import connection
from django.shortcuts import redirect
from django.urls import reverse
from django_tenants.utils import get_public_schema_name
from django.contrib import messages

class AdminAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith('/admin/'):
            user = request.user
            
            # If not authenticated, allow normal login flow
            if not user.is_authenticated:
                return self.get_response(request)

            current_schema = connection.schema_name
            
            if current_schema == get_public_schema_name():
                # On main domain
                if not user.is_superuser:
                    messages.error(request, 'Access denied. Please log in to your hospital domain.')
                    logout(request)
                    return redirect(reverse('admin:login'))
            else:
                # On tenant domain
                if not user.hospital or user.hospital.schema_name != current_schema:
                    messages.error(request, 'Access denied. Please log in to your assigned hospital domain.')
                    logout(request)
                    return redirect(reverse('admin:login'))

        return self.get_response(request)