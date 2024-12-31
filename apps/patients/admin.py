from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.utils.html import format_html
from .models import Patient, PatientDemographics, PatientAddress


class PatientDemographicsInline(admin.StackedInline):
    model = PatientDemographics
    can_delete = False
    verbose_name_plural = "Demographics"


class PatientAddressInline(admin.StackedInline):
    model = PatientAddress
    extra = 0


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "email",
        "phone_primary",
        "date_of_birth",
        "status_badge",
    )
    list_filter = ("is_active", "preferred_language", "created_at")
    search_fields = ("first_name", "last_name", "email")
    inlines = [PatientDemographicsInline, PatientAddressInline]
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        (
            "Basic Information",
            {
                "fields": (
                    ("first_name", "middle_name", "last_name"),
                    ("date_of_birth", "gender"),
                    "preferred_language",
                )
            },
        ),
        (
            "Contact Information",
            {"fields": (("email", "phone_primary"), "phone_secondary")},
        ),
        (
            "System Information",
            {
                "classes": ("collapse",),
                "fields": ("created_at", "updated_at", "is_active"),
            },
        ),
    )

    def full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"

    def status_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 3px 10px; border-radius: 10px;">'
                "Active</span>"
            )
        return format_html(
            '<span style="background-color: #dc3545; color: white; padding: 3px 10px; border-radius: 10px;">'
            "Inactive</span>"
        )

    status_badge.short_description = "Status"
