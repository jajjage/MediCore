from apps.patients.models import (
    PatientMedicalReport,
)

from .base_serializer import BasePatientSerializer


class PatientMedicalReportSerializer(BasePatientSerializer):
    """Serializer for patient medical reports."""

    class Meta:
        model = PatientMedicalReport
        fields = ["id", "title", "description", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

