
from django.db import models

from .core import PatientBasemodel


class PatientAllergies(PatientBasemodel):
    patient = models.ForeignKey("Patient", on_delete=models.CASCADE, related_name="allergies")
    name = models.CharField(max_length=100)
    severity = models.CharField(
        max_length=50,
        choices=[("Mild", "Mild"), ("Moderate", "Moderate"), ("Severe", "Severe")],
    )
    reaction = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "patient_allergies"
        indexes = [
            models.Index(fields=["patient"]),  # Index for filtering by patient
            models.Index(fields=["name"]),  # Index for allergy name
            models.Index(fields=["severity"]),  # Index for filtering by severity
        ]

class PatientChronicCondition(PatientBasemodel):
    patient = models.ForeignKey("Patient", on_delete=models.CASCADE, related_name="chronic_conditions")
    condition = models.CharField(max_length=100)
    diagnosis_date = models.DateField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "patient_chronic_conditions"
        indexes = [
            models.Index(fields=["patient"]),  # Index for filtering by patient
            models.Index(fields=["condition"]),  # Index for condition name
            models.Index(fields=["diagnosis_date"]),  # Index for filtering by diagnosis date
        ]
