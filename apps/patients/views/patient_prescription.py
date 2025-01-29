
from rest_framework.exceptions import ValidationError

from apps.patients.models import (
    PatientAppointment,
    PatientPrescription,
)
from apps.patients.serializers import (
    PatientPrescriptionSerializer,
)
from base_view import BaseViewSet


class PatientPrescriptionViewSet(BaseViewSet):
    """
    A viewset for managing Prescription instances with optimized querying.

    Supports both patient-specific and individual prescription retrieval.
    """

    serializer_class = PatientPrescriptionSerializer


    def get_queryset(self):
        patient_id = self.kwargs.get("patient_pk")
        if patient_id:
            return PatientPrescription.objects.select_related(
                "appointment__patient",
                "issued_by"
            ).filter(appointment__patient_id=patient_id)

        return PatientPrescription.objects.select_related(
            "appointment__patient",
            "issued_by"
        )

    def get_latest_appointment(self, patient_id):
        """
        Get the latest appointment for the patient that doesn't have a prescription.
        """
        return PatientAppointment.objects.filter(
            patient_id=patient_id,
            prescription__isnull=True
        ).order_by("-appointment_date").first()

    def perform_create(self, serializer):
        """
        Hanf Creates a prescription for a specific patient's appointment.
        """
        patient_id = self.kwargs.get("patient__pk")
        if not patient_id:
            raise ValidationError("Patient ID is required for creating a prescription")

        # Get the latest appointment without a prescription
        appointment = self.get_latest_appointment(patient_id)
        if not appointment:
            raise ValidationError("No available appointments found for prescription creation")

        # Get the staff member instance
        try:
            staff_member = self.request.user
            if not staff_member:
                raise ValidationError("Current user is not associated with a staff member")
        except AttributeError as err:
            raise ValidationError("Current user is not associated with a staff member") from err

        # Save with both appointment and issued_by
        serializer.save(
            appointment=appointment,
            issued_by=staff_member
        )

