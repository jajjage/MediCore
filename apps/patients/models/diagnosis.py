import uuid

from django.db import models
from simple_history.models import HistoricalRecords

from .core import Patient


class PatientDiagnosis(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(
        Patient, on_delete=models.CASCADE, related_name="diagnoses"
    )
    diagnosis_date = models.DateField()
    diagnosis_name = models.CharField(max_length=255)
    icd_code = models.CharField(max_length=20, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    history = HistoricalRecords(user_model="staff.StaffMember")

    class Meta:
        db_table = "patient_diagnoses"
        indexes = [
            models.Index(fields=["patient"]),  # Index for filtering by patient
            models.Index(fields=["diagnosis_date"]),  # Index for filtering/sorting by diagnosis date
            models.Index(fields=["diagnosis_name"]),  # Index for searching/filtering by diagnosis name
            models.Index(fields=["icd_code"]),  # Index for filtering by ICD code
        ]


    def __str__(self):
        return f"Diagnosis: {self.diagnosis_name} for {self.patient.first_name}"
