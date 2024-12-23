from django.contrib import admin

from .models import HospitalProfile

@admin.register(HospitalProfile)
class HospitalProfileAdmin(admin.ModelAdmin):
    list_display = ('hospital_name', 'subscription_plan', 'contact_email', 'created_at')
    readonly_fields = ('tenant', 'admin_user', 'created_at', 'updated_at')
    
    def has_add_permission(self, request):
        # Only superuser can add hospital profiles
        return request.user.is_superuser
    
    def has_delete_permission(self, request, obj=None):
        # Only superuser can delete hospital profiles
        return request.user.is_superuser
