import uuid

from django.db import models
from simple_history.models import HistoricalRecords

from .core import Patient


class PatientOperation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="operations")
    operation_date = models.DateField(db_index=True)
    surgeon = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    operation_name = models.CharField(max_length=255)
    operation_code = models.CharField(max_length=50, blank=True, null=True)
    notes = models.TextField(blank=True, null=True, db_index=True)
    history = HistoricalRecords(user_model="staff.StaffMember")

    class Meta:
        db_table = "patient_operations"  # Specify the table name
        indexes = [
            models.Index(fields=["operation_date", "surgeon"]),
            models.Index(fields=["operation_name", "operation_code"]),
        ]


    def __str__(self):
        return f"Operation: {self.operation_name} for {self.patient.first_name}"
