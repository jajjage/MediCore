import uuid

from django.db import models
from simple_history.models import HistoricalRecords

from .core import Patient


class PatientEmergencyContact(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.OneToOneField(Patient, on_delete=models.CASCADE, related_name="emergency_contact")
    name = models.CharField(max_length=100, blank=True, null=True)
    history = HistoricalRecords(user_model="staff.StaffMember")
    phone = models.CharField(max_length=20, blank=True, null=True)
    relationship = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        db_table = "patient_emergency_contacts"  # Specify table name

