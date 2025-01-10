from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django_tenants.models import get_tenant_domain_model
from django_tenants.utils import schema_context

from hospital.models import HospitalProfile

from .models import Department, DepartmentMember, StaffMember, StaffRole


@admin.register(StaffMember)
class StaffMemberAdmin(admin.ModelAdmin):
    list_display = ("email", "full_name", "role", "hospital", "is_active", "primary_department", "roles_display")
    list_filter = ("is_active", "hospital", "is_staff", "department_memberships__department")

    fieldsets = (
        (None, {
            "fields": ("email", "password")
        }),
        (_("Personal info"), {
            "fields": ("first_name", "last_name", "hospital", "role")
        }),
        (_("Permissions"), {
            "fields": ("is_active",),
        }),
        (_("Important dates"), {
            "fields": ("last_login", "date_joined")
        }),
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
        """Customize the form to associate the hospital with the current schema's hospital."""
        form = super().get_form(request, obj, **kwargs)
        tenant_domain = get_tenant_domain_model().objects.get(
            domain=request.get_host().split(":")[0]
        )
        with schema_context(tenant_domain.tenant.schema_name):
            hospital = HospitalProfile.objects.get(tenant_id=tenant_domain.tenant.id)

        if not obj:
            form.base_fields["hospital"].initial = hospital
            form.base_fields["hospital"].widget.attrs["readonly"] = True
            form.base_fields["hospital"].widget.attrs["disabled"] = True
        else:
            form.base_fields["hospital"].initial = hospital
            form.base_fields["hospital"].widget.attrs["readonly"] = True
            form.base_fields["hospital"].widget.attrs["disabled"] = True

        return form

    def save_model(self, request, obj, form, change):
        """Automatically set the hospital field to the current schema's hospital during save."""
        if not change:  # If creating a new instance
            tenant_domain = get_tenant_domain_model().objects.get(
                domain=request.get_host().split(":")[0]
            )
            with schema_context(tenant_domain.tenant.schema_name):
                hospital = HospitalProfile.objects.get(
                    tenant_id=tenant_domain.tenant.id
                )
            obj.hospital = hospital

        if form.cleaned_data.get("password"):
            obj.set_password(form.cleaned_data["password"])

        super().save_model(request, obj, form, change)

    def get_queryset(self, request):
        """Ensure that the queryset only returns staff members for the current hospital."""
        qs = super().get_queryset(request)
        tenant_domain = get_tenant_domain_model().objects.get(
            domain=request.get_host().split(":")[0]
        )
        with schema_context(tenant_domain.tenant.schema_name):
            hospital = HospitalProfile.objects.get(tenant_id=tenant_domain.tenant.id)
            return qs.filter(hospital=hospital)

    def full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
    full_name.short_description = _("Full Name")

    def primary_department(self, obj):
        primary = obj.department_memberships.filter(is_primary=True).first()
        if primary:
            return primary.department.name
        return "-"
    primary_department.short_description = _("Primary Department")

    def roles_display(self, obj):
        roles = obj.department_memberships.values_list("role", flat=True).distinct()
        return ", ".join(roles) if roles else "-"
    roles_display.short_description = _("Roles")

@admin.register(StaffRole)
class StaffRoleAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "permission_count")
    search_fields = ("name", "code")
    filter_horizontal = ("permissions",)

    def permission_count(self, obj):
        return obj.permissions.count()
    permission_count.short_description = _("Permissions")

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "department_type", "hospital", "staff_count_display",
                   "department_head_display", "is_active")
    list_filter = ("department_type", "hospital", "is_active")
    search_fields = ("name", "code", "description")
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        (None, {
            "fields": ("name", "code", "department_type", "hospital")
        }),
        (_("Hierarchy"), {
            "fields": ("parent_department",),
        }),
        (_("Details"), {
            "fields": ("description", "location", "contact_email", "contact_phone")
        }),
        (_("Management"), {
            "fields": ("department_head", "is_active")
        }),
        (_("Timestamps"), {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )

    def get_form(self, request, obj=None, **kwargs):
        """Customize the form to associate the hospital with the current schema's hospital."""
        form = super().get_form(request, obj, **kwargs)
        tenant_domain = get_tenant_domain_model().objects.get(
            domain=request.get_host().split(":")[0]
        )
        with schema_context(tenant_domain.tenant.schema_name):
            hospital = HospitalProfile.objects.get(tenant_id=tenant_domain.tenant.id)

        # Always set the hospital field
        form.base_fields["hospital"].initial = hospital
        form.base_fields["hospital"].widget.attrs["readonly"] = True
        form.base_fields["hospital"].widget.attrs["disabled"] = True
        # Important: Make the hospital field not required in the form since we're setting it in save_model
        form.base_fields["hospital"].required = False

        return form

    def save_model(self, request, obj, form, change):
        """Automatically set the hospital field to the current schema's hospital during save."""
        tenant_domain = get_tenant_domain_model().objects.get(
            domain=request.get_host().split(":")[0]
        )
        with schema_context(tenant_domain.tenant.schema_name):
            hospital = HospitalProfile.objects.get(
                tenant_id=tenant_domain.tenant.id
            )
        obj.hospital = hospital

        # Let the parent class handle the actual save
        super().save_model(request, obj, form, change)

    def get_queryset(self, request):
        """Ensure that the queryset only returns staff members for the current hospital."""
        qs = super().get_queryset(request)
        tenant_domain = get_tenant_domain_model().objects.get(
            domain=request.get_host().split(":")[0]
        )
        with schema_context(tenant_domain.tenant.schema_name):
            hospital = HospitalProfile.objects.get(tenant_id=tenant_domain.tenant.id)
            return qs.filter(hospital=hospital)

    def staff_count_display(self, obj):
        count = obj.get_staff_count()
        url = reverse("admin:staff_departmentmember_changelist") + f"?department__id={obj.id}"
        return format_html('<a href="{}">{} staff members</a>', url, count)
    staff_count_display.short_description = _("Staff Count")

    def department_head_display(self, obj):
        if obj.department_head:
            url = reverse("admin:staff_staffmember_change", args=[obj.department_head.id])
            return format_html('<a href="{}">{}</a>', url, obj.department_head.get_full_name())
        return "-"
    department_head_display.short_description = _("Department Head")

@admin.register(DepartmentMember)
class DepartmentMemberAdmin(admin.ModelAdmin):
    list_display = ("user_display", "department_display", "role", "is_primary",
                   "start_date", "end_date", "is_active")
    list_filter = ("is_active", "is_primary", "role", "department")
    search_fields = ("user__email", "user__first_name", "user__last_name",
                    "department__name")
    date_hierarchy = "start_date"

    fieldsets = (
        (None, {
            "fields": ("user", "department", "role")
        }),
        (_("Assignment Details"), {
            "fields": ("start_date", "end_date", "is_primary")
        }),
        (_("Status"), {
            "fields": ("is_active",)
        }),
    )

    def user_display(self, obj):
        url = reverse("admin:staff_staffmember_change", args=[obj.user.id])
        return format_html('<a href="{}">{}</a>',
                         url, obj.user.get_full_name() or obj.user.email)
    user_display.short_description = _("Staff Member")

    def department_display(self, obj):
        url = reverse("admin:staff_department_change", args=[obj.department.id])
        return format_html('<a href="{}">{}</a>', url, obj.department.name)
    department_display.short_description = _("Department")
