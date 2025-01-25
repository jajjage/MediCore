from django.contrib import admin


class TenantAwareAdminSite(admin.AdminSite):
    pass
# Replace default admin site
admin_site = TenantAwareAdminSite(name="tenant_admin")
admin.site = admin_site  # Monkey-patch if necessary
