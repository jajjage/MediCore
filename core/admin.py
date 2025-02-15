from django.contrib import admin

from .models import ModelPermission, MyUser, TenantPermission

admin.site.register(TenantPermission)
admin.site.register(ModelPermission)
class CustomUserAdmin(admin.ModelAdmin):  # Changed from UserAdmin to admin.ModelAdmin
    list_display = ["email", "hospital", "is_superuser", "is_tenant_admin"]
    list_filter = ["is_superuser", "is_tenant_admin"]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "is_tenant_admin",
                    "hospital",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "password1",
                    "password2",
                    "hospital",
                    "is_tenant_admin",
                    "is_active",
                    "is_staff",
                ),
            },
        ),
    )
    search_fields = ["email"]
    ordering = ["email"]
    filter_horizontal = (
        "groups",
        "user_permissions",
    )  # These will now work with PermissionsMixin


    def save_model(self, request, obj, form, change):
        if form.cleaned_data.get("password"):
            obj.set_password(form.cleaned_data["password"])

        super().save_model(request, obj, form, change)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.none()

    def has_module_permission(self, request):
        # Only superuser can see Users in admin
        return request.user.is_superuser


admin.site.register(MyUser, CustomUserAdmin)
