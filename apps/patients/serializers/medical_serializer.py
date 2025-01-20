from rest_framework import serializers

from apps.patients.models import (
    PatientAllergies,
    PatientChronicConditions,
)

from .base_serializer import BasePatientSerializer


class PatientAllergySerializer(BasePatientSerializer):
    """Serializer for patient allergies."""

    class Meta:
        model = PatientAllergies
        fields = ["id", "name", "severity", "reaction"]
        read_only_fields = ["id"]

    def validate_severity(self, value):
        valid_severities = dict(PatientAllergies._meta.get_field("severity").choices)
        if value not in valid_severities:
            raise serializers.ValidationError(
                f"'{value}' is not a valid severity. Use one of {list(valid_severities.keys())}."
            )
        return value


class PatientChronicConditionSerializer(BasePatientSerializer):
    """Serializer for patient chronic conditions."""

    class Meta:
        model = PatientChronicConditions
        fields = ["id", "condition", "diagnosis_date", "notes"]
        read_only_fields = ["id"]

    def validate_diagnosis_date(self, value):
        return self.validate_future_date(value, "Diagnosis date")


