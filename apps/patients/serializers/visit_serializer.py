from rest_framework import serializers

from apps.patients.models import (
    PatientVisit,
)

from .base_serializer import BasePatientSerializer


class PatientVisitSerializer(BasePatientSerializer):
    """
    Serializer for patient visits with validation and history tracking.
    """

    class Meta:
        model = PatientVisit
        fields = [
            "id",
            "visit_date",
            "ward_or_clinic",
            "discharge_date",
            "discharge_notes",
            "referred_by",
        ]
        read_only_fields = ["id", "patient",  "physician"]

    def validate(self, data):
        """
        Validate visit dates and permissions.
        """
        visit_date = data.get("visit_date")
        discharge_date = data.get("discharge_date")

        if visit_date and discharge_date and discharge_date < visit_date:
            raise serializers.ValidationError({
                "discharge_date": "Discharge date cannot be earlier than visit date."
            })

        # Ensure user has proper permissions
        if self.instance:
            if not self.check_permission("change", "patientvisit"):
                raise serializers.ValidationError(
                    {"error": "You don't have permission to update visits"}
                )
        elif not self.check_permission("add", "patientvisit"):
            raise serializers.ValidationError(
                {"error": "You don't have permission to add visits"}
            )

        return data

    def to_representation(self, instance):
        """
        Control data visibility based on permissions.
        """
        if not self.check_permission("view", "patientvisit"):
            return {}
        return super().to_representation(instance)
