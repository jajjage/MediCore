from rest_framework import serializers

from apps.patients.mixins.patients_mixins import (
    PatientCalculationMixin,
)
from apps.patients.models import (
    PatientOperation,
)

from .base_serializer import BasePatientSerializer


class PatientOperationSerializer(BasePatientSerializer, PatientCalculationMixin):
    """
    Serializer for patient operations with validation and history tracking.
    """

    surgeon_full_name = serializers.SerializerMethodField()
    patient_full_name = serializers.SerializerMethodField()
    class Meta:
        model = PatientOperation
        fields = [
            "id",
            "patient_full_name",
            "surgeon_full_name",
            "operation_date",
            "operation_time",
            "operation_name",
            "operation_code",
            "status",
            "notes",
        ]
        read_only_fields = ["id"]

    def validate(self, data):
        """Validate operation data and permissions."""
        if self.instance:
            if not self.check_permission("change", "patientoperation"):
                raise serializers.ValidationError(
                    {"error": "You don't have permission to update operations"}
                )
        elif not self.check_permission("add", "patientoperation"):
            raise serializers.ValidationError(
                {"error": "You don't have permission to add operations"}
            )

        return data

    def get_surgeon_full_name(self, obj):
        return self.physician_format_full_name(
            obj.surgeon.first_name,
            obj.surgeon.last_name
        )

    def get_patient_full_name(self, obj):
        return self.format_full_name(
            obj.patient.first_name,
            obj.patient.middle_name,
            obj.patient.last_name
        )
