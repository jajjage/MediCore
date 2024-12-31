from django.contrib import admin
from django.contrib import messages
from django.db import transaction
from tenants.models import Client
from .models import HospitalProfile
from core.models import MyUser


@admin.register(HospitalProfile)
class HospitalProfileAdmin(admin.ModelAdmin):
    list_display = [
        "hospital_name",
        "subscription_plan",
        "license_number",
        "contact_email",
        "created_at",
    ]
    list_filter = ["subscription_plan", "created_at"]
    search_fields = ["hospital_name", "license_number", "contact_email"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        (
            "Hospital Information",
            {
                "fields": (
                    "hospital_name",
                    "license_number",
                    "specialty",
                    "bed_capacity",
                )
            },
        ),
        (
            "Contact Information",
            {
                "fields": (
                    "contact_email",
                    "contact_phone",
                    "address",
                )
            },
        ),
        (
            "Subscription",
            {
                "fields": ("subscription_plan",),
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def save_model(self, request, obj, form, change):
        try:
            with transaction.atomic():
                if not change:  # Only for new hospitals
                    # Create the tenant
                    schema_name = self.generate_schema_name(obj.hospital_name)
                    domain_url = f"{schema_name}.example.com"  # Adjust domain as needed

                    tenant = Client.objects.create(
                        schema_name=schema_name,
                        name=obj.hospital_name,
                        domain_url=domain_url,
                    )

                    # Create the tenant admin user
                    admin_user = MyUser.objects.create_tenant_admin(
                        email=obj.contact_email,
                        hospital=tenant,
                        password="changeme123",  # Temporary password
                    )

                    # Link everything to the hospital profile
                    obj.tenant = tenant
                    obj.admin_user = admin_user

                super().save_model(request, obj, form, change)

                if not change:
                    messages.success(
                        request,
                        f"Hospital {obj.hospital_name} created successfully. "
                        f"Admin user can login with email: {obj.contact_email} "
                        f"and temporary password: changeme123",
                    )

        except Exception as e:
            messages.error(request, f"Error creating hospital: {str(e)}")
            raise

    def generate_schema_name(self, hospital_name):
        """Generate a valid schema name from hospital name"""
        # Convert to lowercase and replace spaces with underscores
        schema_name = hospital_name.lower().replace(" ", "_")
        # Remove any non-alphanumeric characters except underscore
        schema_name = "".join(c for c in schema_name if c.isalnum() or c == "_")
        # Ensure it's unique
        base_name = schema_name
        counter = 1
        while Client.objects.filter(schema_name=schema_name).exists():
            schema_name = f"{base_name}_{counter}"
            counter += 1
        return schema_name

    def has_module_permission(self, request):
        """Only superuser can see this module in admin"""
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
