from django.contrib import admin


class CustomAdminSite(admin.AdminSite):

    def has_permission(self, request):
        """
        Check if user has permission to access the admin site.

        Allow access for superusers, staff, and tenant admins.
        """
        return request.user.is_authenticated and (request.user.is_superuser or request.user.is_staff or (
            hasattr(request.user, "is_tenant_admin") and request.user.is_tenant_admin
        ))

    def get_app_list(self, request, app_label=None):
        """
        Filter apps based on user permissions and role.
        """
        full_app_list = super().get_app_list(request, app_label)

        # Superusers see everything
        if request.user.is_superuser:
            return full_app_list

        # Tenant admins and staff see allowed apps
        if (hasattr(request.user, "is_tenant_admin") and request.user.is_tenant_admin) or request.user.is_staff:
            # Define apps that tenant admins/staff can see
            allowed_apps = {
                "patients",      # Patient management
                "appointments",  # Appointment management
                "staff",         # Staff management
                # Add other apps that tenant admins should see
            }

            # Filter app list
            filtered_app_list = []
            for app in full_app_list:
                if app["app_label"] in allowed_apps:
                    # Check model-level permissions
                    filtered_models = []
                    for model in app["models"]:
                        model_name = model["object_name"].lower()
                        # Check if user has any permissions for this model
                        if any(
                            request.user.has_perm(f"{app['app_label']}.{perm}_{model_name}")
                            for perm in ["view", "add", "change", "delete"]
                        ):
                            filtered_models.append(model)

                    if filtered_models:
                        app["models"] = filtered_models
                        filtered_app_list.append(app)

            return filtered_app_list

        return []  # No apps for non-staff, non-tenant-admin users
