# models/staff_profiles.py

from django.db import models

from .core import StaffProfile


class DoctorProfile(StaffProfile):
    """Profile specific to doctors."""

    specialization = models.CharField(max_length=100)
    license_number = models.CharField(max_length=50, unique=True)
    availability = models.JSONField(
        default=dict,
        help_text="Weekly schedule in JSON format"
    )
    consulting_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    max_patients_per_day = models.PositiveIntegerField(default=20)

    class Meta:
        db_table = "doctor_profile"

class NurseProfile(StaffProfile):
    """Profile specific to nurses."""

    nurse_license = models.CharField(max_length=50, unique=True)
    ward_specialty = models.CharField(max_length=100)
    class Meta:
        db_table = "nurse_profile"

class TechnicianProfile(StaffProfile):
    """Profile specific to technicians."""

    technician_license = models.CharField(max_length=50, unique=True)
    equipment_specialties = models.JSONField(
        default=list,
        help_text="List of equipment specialties"
    )
    lab_certifications = models.JSONField(
        default=list,
        help_text="List of laboratory certifications"
    )

    class Meta:
        db_table = "technician_profile"
