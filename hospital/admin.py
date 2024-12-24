from django.contrib import admin
from django_tenants.utils import get_public_schema_name
from django.db import connection
from .models import HospitalProfile

@admin.register(HospitalProfile)
class HospitalProfileAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if connection.schema_name == get_public_schema_name():
            # On main domain, superuser can see all profiles
            return qs
        # On tenant domain, only show current tenant's profile
        return qs.filter(tenant__schema_name=connection.schema_name)

    def has_add_permission(self, request):
        # Only allow adding profiles from main domain
        return connection.schema_name == get_public_schema_name()
