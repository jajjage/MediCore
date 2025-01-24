
from django.db import models
from django.utils import timezone

from .core import Basemodel


class PatientOperation(Basemodel):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    surgeon = models.ForeignKey(
        "staff.DoctorProfile",
        on_delete=models.CASCADE,
        related_name="operations",
        limit_choices_to={"role__name__in": ["Doctor", "Head Doctor"]},
        db_index=True
    )
    operation_date = models.DateField()
    operation_time = models.TimeField()
    operation_name = models.CharField(max_length=255)
    operation_code = models.CharField(max_length=50, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
        default="pending",
        db_index=True
    )
    created_at = models.DateTimeField(default=timezone.now)  # Changed to have a default
    updated_at = models.DateTimeField(default=timezone.now)  # Changed to have a default


    class Meta:
        db_table = "patient_operations"
        indexes = [
            models.Index(fields=["operation_date", "operation_name"]),
            models.Index(fields=["operation_code"]),
        ]
        ordering = ["-operation_date", "-operation_time"]

    def __str__(self):
        return f"Operation: {self.operation_name} for {self.patient.first_name}"

    def save(self, *args, **kwargs):
        # if self.operation_code:
        #     self.operation_code = self.operation_code.upper()
        if not self.pk:  # If creating a new object
            self.created_at = timezone.now()
        self.updated_at = timezone.now()
        super().save(*args, **kwargs)
