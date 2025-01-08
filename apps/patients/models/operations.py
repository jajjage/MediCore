import uuid

from django.db import models
from simple_history.models import HistoricalRecords

from .core import Patient


class PatientOperation(models.Model):

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="operations")
    surgeon = models.ForeignKey(
        "staff.StaffMember",
        on_delete=models.CASCADE,
        related_name="operations",
        limit_choices_to={"role__name": ["Doctor", "Head Doctor"]}, db_index=True, null=True)
    operation_date = models.DateField()

    operation_name = models.CharField(max_length=255)
    operation_code = models.CharField(max_length=50, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    status = models.CharField(
        max_length=50, choices=STATUS_CHOICES, default="pending"
    )
    modified_by = models.ForeignKey(
        "staff.StaffMember", on_delete=models.SET_NULL, null=True, related_name="modified_operations"
    )
    history = HistoricalRecords(user_model="staff.StaffMember")

    class Meta:
        db_table = "patient_operations"  # Specify the table name
        indexes = [
            models.Index(fields=["operation_date", "operation_name"]),
            models.Index(fields=["operation_code"]),
        ]


    def __str__(self):
        return f"Operation: {self.operation_name} for {self.patient.first_name}"
