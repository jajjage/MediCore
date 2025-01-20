from rest_framework import serializers

from apps.patients.mixins.patients_mixins import (
    PatientCalculationMixin,
)
from apps.patients.model_perm import prescription_period
from apps.patients.models import (
    PatientPrescription,
)

from .base_serializer import BasePatientSerializer


class PatientPrescriptionSerializer(BasePatientSerializer, PatientCalculationMixin):
    physician_full_name = serializers.SerializerMethodField()
    class Meta:
        model = PatientPrescription
        fields = [
            "id",
            "appointment",
            "physician_full_name",
            "medicines",
            "instructions",
            "issued_date",
            "valid_until",
        ]
        read_only_fields = ["id", "issued_date", "issued_by", "appointment"]

    def validate(self, data):
        """
        Perform custom validation.
        """
        # Ensure valid_until date is not earlier than issued_date
        data = prescription_period(data)

        return data

    def validate_appointment(self, value):
        """
        Ensure the appointment has no existing prescription.
        """
        if value.prescription.exists():
            raise serializers.ValidationError(
                "A prescription already exists for this appointment."
            )
        return value

    def get_physician_full_name(self, obj):
        return self.physician_format_full_name(obj.issued_by.first_name, obj.issued_by.last_name)
