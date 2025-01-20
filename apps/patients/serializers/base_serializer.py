from django.utils.timezone import now
from rest_framework import serializers

from apps.patients.permissions import PermissionCheckedSerializerMixin


class BasePatientSerializer(
    PermissionCheckedSerializerMixin, serializers.ModelSerializer
):
    """Base serializer with common patient-related functionality."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_permissions()

    def set_permissions(self):
        """Set field permissions based on user access."""
        model_name = self.Meta.model._meta.model_name
        if not self.check_permission("change", model_name):
            for field_name in self.fields:
                self.fields[field_name].read_only = True

    def validate_date_not_future(self, value, field_name):
        """Common validation for future dates."""  # noqa: D401
        if value and value > now().date():
            raise serializers.ValidationError(f"{field_name} cannot be in the future.")
        return value
