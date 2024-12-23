from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import MyUser

class UserAdmin(BaseUserAdmin):
    list_display = ("email", "role", "staff_role", "is_admin", "is_superuser")
    list_filter = ("is_admin", "role", "staff_role")
    fieldsets = (
        (None, {"fields": ("email", "password")}),

        ("Permissions", {"fields": ("is_admin", "is_superuser", "role", "staff_role")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "role", "staff_role", "password1", "password2"),
        }),
    )
    search_fields = ("email",)
    ordering = ("email",)
    filter_horizontal = ()

admin.site.register(MyUser, UserAdmin)
