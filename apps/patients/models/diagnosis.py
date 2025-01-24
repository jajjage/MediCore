
from django.db import models

from .core import Basemodel


class PatientDiagnoses(Basemodel):
    diagnosis_date = models.DateField()
    diagnosis_name = models.CharField(max_length=255)
    icd_code = models.CharField(max_length=20, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)


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
