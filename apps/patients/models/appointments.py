import uuid

from django.db import models
from simple_history.models import HistoricalRecords

from .core import Patient


class PatientAppointment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="appointments")
    appointment_date = models.DateTimeField()
    reason = models.CharField(max_length=255)
    physician = models.CharField(max_length=100)
    status = models.CharField(
        max_length=50, choices=[("Pending", "Pending"), ("Completed", "Completed")]
    )
    notes = models.TextField(blank=True, null=True)
    history = HistoricalRecords(user_model="staff.StaffMember")

    class Meta:
        db_table = "patient_appointments"  # Specify table name
        indexes = [
            models.Index(fields=["appointment_date", "physician"]),
            models.Index(fields=["status", "appointment_date"]),
        ]


    def __str__(self):
        return f"Appointment on {self.appointment_date} for {self.patient.first_name}"
