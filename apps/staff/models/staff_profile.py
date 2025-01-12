# models/staff_profiles.py
import uuid

from django.db import models


class StaffProfile(models.Model):
    """Base model for all staff profiles."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    qualification = models.CharField(max_length=255)
    years_of_experience = models.PositiveIntegerField()
    certification_number = models.CharField(max_length=100, blank=True)
    specialty_notes = models.TextField(blank=True)

    class Meta:
        abstract = True

class DoctorProfile(StaffProfile):
    """Profile specific to doctors."""

    staff_member = models.OneToOneField(
        "StaffMember",
        on_delete=models.CASCADE,
        related_name="doctor_profile"
    )
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

    staff_member = models.OneToOneField(
        "StaffMember",
        on_delete=models.CASCADE,
        related_name="nurse_profile"
    )
    nurse_license = models.CharField(max_length=50, unique=True)
    ward_specialty = models.CharField(max_length=100)
    shift_preferences = models.JSONField(
        default=dict,
        help_text="Shift preferences in JSON format"
    )

    class Meta:
        db_table = "nurse_profile"

class TechnicianProfile(StaffProfile):
    """Profile specific to technicians."""

    staff_member = models.OneToOneField(
        "StaffMember",
        on_delete=models.CASCADE,
        related_name="technician_profile"
    )
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
