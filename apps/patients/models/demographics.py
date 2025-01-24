
from django.db import models

from .core import Basemodel


class PatientDemographics(Basemodel):
    blood_type = models.CharField(max_length=5, blank=True, null=True)
    height_cm = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    weight_kg = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    gender = models.CharField(max_length=50, blank=True, null=True)
    race = models.CharField(max_length=50, blank=True, null=True)
    ethnicity = models.CharField(max_length=50, blank=True, null=True)
    preferred_language = models.CharField(max_length=50, blank=True, null=True)
    marital_status = models.CharField(max_length=50, blank=True, null=True)
    employment_status = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "patient_demographics"
        indexes = [
            models.Index(fields=["gender"]),  # Index on gender for quick filtering
            models.Index(fields=["blood_type"]),  # Index on blood type for filtering
            models.Index(fields=["preferred_language"]),  # Index for querying language
            models.Index(fields=["marital_status"]),  # Index marital status for analytics
            models.Index(fields=["created_at"]),  # Index for querying by creation date
        ]
        permissions = [
            ("view_patient", "Can view patient"),
            ("view_patient_demographics", "Can view patient demographics"),
        ]
