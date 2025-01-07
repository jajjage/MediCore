import uuid

from django.db import models


class PatientPrescription(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    appointment = models.OneToOneField(
        "PatientAppointment", on_delete=models.CASCADE, related_name="prescription"
    )
    issued_by = models.ForeignKey(
        "staff.StaffMember",
        on_delete=models.CASCADE,
        related_name="issued_prescriptions",
        limit_choices_to={"role__name": "Doctor"},
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
