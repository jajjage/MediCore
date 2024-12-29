# core/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from .models import MyUser
from .forms import UserChangeForm, UserCreationForm
from django.db import connection
from django_tenants.utils import get_public_schema_name

@admin.register(MyUser)
class CustomUserAdmin(admin.ModelAdmin):  # Changed from UserAdmin to admin.ModelAdmin
    form = UserChangeForm
    add_form = UserCreationForm
    list_display = ('email', 'role', 'staff_role', 'is_admin', 'is_active')
    list_filter = ('role', 'staff_role', 'is_admin', 'is_active')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',)

    # Define fieldsets for add/change forms
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name')}),
        (_('Roles'), {'fields': ('role', 'staff_role')}),
        (_('Permissions'), {'fields': ('is_active', 'is_admin', 'is_superuser')}),
    )

    # Fields for creating a new user
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'role', 'staff_role'),
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if connection.schema_name == get_public_schema_name():
            # On main domain, show all users except tenant users
            return qs.filter(hospital__isnull=True)
        # On tenant domain, only show users of current tenant
        return qs.filter(hospital__schema_name=connection.schema_name)

    def has_change_permission(self, request, obj=None):
        if connection.schema_name == get_public_schema_name():
            return request.user.is_superuser
        return request.user.is_admin

    def get_fieldsets(self, request, obj=None):
        if not obj:
            return self.add_fieldsets
        return super().get_fieldsets(request, obj)

    def get_form(self, request, obj=None, **kwargs):
        """
        Use special form during user creation
        """
        defaults = {}
        if obj is None:
            defaults['form'] = self.add_form
        defaults.update(kwargs)
        return super().get_form(request, obj, **defaults)