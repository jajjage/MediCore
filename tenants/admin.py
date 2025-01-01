from django.contrib import admin
from .models import Client, Domain


class TenantAdmin(admin.ModelAdmin):
    list_display = ("name", "schema_name", "created_at")
    search_fields = ("name", "schema_name")


class DomainAdmin(admin.ModelAdmin):
    list_display = ("domain", "tenant")
    search_fields = ("domain", "tenant__name")


admin.site.register(Client, TenantAdmin)
admin.site.register(Domain, DomainAdmin)
