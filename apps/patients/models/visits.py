import uuid

from django.db import models
from simple_history.models import HistoricalRecords

from .core import Patient


class PatientVisit(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="visits")
    visit_date = models.DateTimeField(db_index=True)
    physician = models.CharField(max_length=100, blank=True, null=True)
    ward_or_clinic = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    discharge_date = models.DateTimeField(blank=True, null=True, db_index=True)
    discharge_notes = models.TextField(blank=True, null=True)
    referred_by = models.CharField(max_length=255, blank=True, null=True)
    history = HistoricalRecords(user_model="staff.StaffMember")

    class Meta:
        db_table="patient_visits"
        indexes = [
            models.Index(fields=["visit_date", "ward_or_clinic"]),
            models.Index(fields=["discharge_date", "patient"]),
        ]


    def __str__(self):
        return f"Visit on {self.visit_date} for {self.patient.first_name}"
