
from django.db import models

from .core import PatientBasemodel


class PatientMedicalReport(PatientBasemodel):
    patient = models.ForeignKey("Patient", on_delete=models.CASCADE, related_name="medical_reports")
    title = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField()

    class Meta:
        db_table = "patient_medical_reports"
        indexes = [
            models.Index(fields=["patient"]),  # Index for filtering by patient
            models.Index(fields=["title"]),  # Index for searching by report title
            models.Index(fields=["created_at"]),  # Index for sorting/filtering by creation date
            models.Index(fields=["updated_at"]),  # Index for sorting/filtering by last update date
        ]

    def __str__(self):
        return f"{self.title} for {self.patient.first_name} {self.patient.last_name}"
