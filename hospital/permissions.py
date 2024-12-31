from rest_framework.permissions import BasePermission


class IsSuperuser(BasePermission):
    """
    Custom permission to allow only superusers to access the view.
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_superuser
