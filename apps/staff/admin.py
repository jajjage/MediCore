from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django_tenants.utils import get_tenant_domain_model, schema_context

from hospital.models import HospitalProfile

from .models import Department, StaffMember, StaffRole


@admin.register(StaffMember)
class StaffMemberAdmin(UserAdmin):
    list_display = ("email", "get_full_name", "role", "department")
    list_filter = ("role", "department")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name")}),
        ("Staff info", {"fields": ("role", "department", "hospital")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "first_name",
                    "last_name",
                    "email",
                    "password1",
                    "password2",
                    "role",
                    "department",
                    "hospital",
                ),
            },
        ),
    )
    search_fields = ("email", "first_name", "last_name")
    ordering = ("email",)

    def get_form(self, request, obj=None, **kwargs):
        """
        Customize the form to associate the department with the current schema's hospital.

        and make the 'hospital' field readonly or hidden.
        """
        form = super().get_form(request, obj, **kwargs)
        tenant_domain = get_tenant_domain_model().objects.get(
            domain=request.get_host().split(":")[0]
        )

        with schema_context(tenant_domain.tenant.schema_name):
            hospital = HospitalProfile.objects.get(tenant_id=tenant_domain.tenant.id)

        # If the object is being created, set the hospital field to the current schema's hospital.
        if not obj:
            form.base_fields["hospital"].initial = hospital
            form.base_fields["hospital"].widget.attrs["readonly"] = True
            form.base_fields["hospital"].widget.attrs["disabled"] = True
        else:
            # If updating an existing department, set the hospital field to the current schema's hospital
            form.base_fields["hospital"].initial = hospital
            form.base_fields["hospital"].widget.attrs["readonly"] = True
            form.base_fields["hospital"].widget.attrs["disabled"] = True

        return form

    def save_model(self, request, obj, form, change):
        """
        Automatically set the hospital field to the current schema's hospital during save.
        """
        if not change:  # If creating a new instance
            tenant_domain = get_tenant_domain_model().objects.get(
                domain=request.get_host().split(":")[0]
            )
            with schema_context(tenant_domain.tenant.schema_name):
                hospital = HospitalProfile.objects.get(
                    tenant_id=tenant_domain.tenant.id
                )
            obj.hospital = hospital

        # Ensure hospital is set correctly before saving
        obj.save()

        super().save_model(request, obj, form, change)

    def get_tenant(self, request):
        domain = get_tenant_domain_model().objects.get(
            domain=request.get_host().split(":")[0]
        )
        with schema_context("public"):
            hospital = HospitalProfile.objects.get(tenant_id=domain.tenant.id)
            return hospital

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "department":
            hospital = self.get_tenant(request)

            kwargs["queryset"] = Department.objects.filter(hospital=hospital)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        hospital = self.get_tenant(request)
        return qs.filter(department__hospital=hospital)

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"

    get_full_name.short_description = "Full Name"


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "hospital")
    list_filter = ("hospital",)

    def get_form(self, request, obj=None, **kwargs):
        """
        Customize the form to associate the department with the current schema's hospital.

        and make the 'hospital' field readonly or hidden.
        """
        form = super().get_form(request, obj, **kwargs)
        tenant_domain = get_tenant_domain_model().objects.get(
            domain=request.get_host().split(":")[0]
        )

        with schema_context(tenant_domain.tenant.schema_name):
            hospital = HospitalProfile.objects.get(tenant_id=tenant_domain.tenant.id)

        # If the object is being created, set the hospital field to the current schema's hospital.
        if not obj:
            form.base_fields["hospital"].initial = hospital
            form.base_fields["hospital"].widget.attrs["readonly"] = True
            form.base_fields["hospital"].widget.attrs["disabled"] = True
        else:
            # If updating an existing department, set the hospital field to the current schema's hospital
            form.base_fields["hospital"].initial = hospital
            form.base_fields["hospital"].widget.attrs["readonly"] = True
            form.base_fields["hospital"].widget.attrs["disabled"] = True

        return form

    def save_model(self, request, obj, form, change):
        """
        Automatically set the hospital field to the current schema's hospital during save.
        """
        if not change:  # If creating a new instance
            tenant_domain = get_tenant_domain_model().objects.get(
                domain=request.get_host().split(":")[0]
            )
            with schema_context(tenant_domain.tenant.schema_name):
                hospital = HospitalProfile.objects.get(
                    tenant_id=tenant_domain.tenant.id
                )
            obj.hospital = hospital

        # Ensure hospital is set correctly before saving
        obj.save()

        super().save_model(request, obj, form, change)

    def get_queryset(self, request):
        """
        Ensure that the queryset only returns departments for the current hospital.
        """
        qs = super().get_queryset(request)
        tenant_domain = get_tenant_domain_model().objects.get(
            domain=request.get_host().split(":")[0]
        )

        with schema_context(tenant_domain.tenant.schema_name):
            hospital = HospitalProfile.objects.get(tenant_id=tenant_domain.tenant.id)

        return qs.filter(hospital=hospital)


@admin.register(StaffRole)
class StaffRoleAdmin(admin.ModelAdmin):
    list_display = ("name",)
