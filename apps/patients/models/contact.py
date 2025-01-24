
from django.db import models

from .core import Basemodel


class PatientEmergencyContact(Basemodel):
    name = models.CharField(max_length=100, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    relationship = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        db_table = "patient_emergency_contacts"  # Specify table name


