
from django.db import models

from .core import PatientBasemodel


class PatientPrescription(PatientBasemodel):
    patient = models.ForeignKey("Patient", on_delete=models.CASCADE, related_name="prescriptions")
    issued_by = models.ForeignKey(
        "staff.DoctorProfile",
        on_delete=models.CASCADE,
        related_name="issued_prescriptions",
    )
    appointment = models.ForeignKey(
        "patients.PatientAppointment",
        on_delete=models.CASCADE,
        related_name="prescriptions",
    )
    medicines = models.TextField()
    instructions = models.TextField(blank=True, null=True)
    issued_date = models.DateField(auto_now_add=True)
    valid_until = models.DateField(blank=True, null=True)

    class Meta:
        db_table = "patient_prescriptions"
        indexes = [
            models.Index(fields=["appointment"]),  # To link prescriptions to appointments
            models.Index(fields=["issued_by", "issued_date"]),  # For filtering by doctor or date
            models.Index(fields=["issued_date"]),  # For date-based searches
        ]

    def __str__(self):
        return f"Prescription for {self.appointment.patient} (ID: {self.id})"
