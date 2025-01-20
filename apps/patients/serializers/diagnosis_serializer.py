from rest_framework import serializers

from apps.patients.models import (
    PatientDiagnosis,
)

from .base_serializer import BasePatientSerializer


class PatientDiagnosisSerializer(BasePatientSerializer):
    """
    Serializer for patient diagnoses with validation and history tracking.
    """

    class Meta:
        model = PatientDiagnosis
        fields = [
            "id",
            "patient",
            "diagnosis_date",
            "diagnosis_name",
            "icd_code",
            "notes",
        ]
        read_only_fields = ["id"]

    def validate_diagnosis_date(self, value):
        """Validate diagnosis date is not in the future."""
        return self.validate_date_not_future(value, "Diagnosis date")

    def validate(self, data):
        """Validate diagnosis data and permissions."""
        if self.instance:
            if not self.check_permission("change", "patientdiagnosis"):
                raise serializers.ValidationError(
                    {"error": "You don't have permission to update diagnoses"}
                )
        elif not self.check_permission("add", "patientdiagnosis"):
            raise serializers.ValidationError(
                {"error": "You don't have permission to add diagnoses"}
            )

        return data
