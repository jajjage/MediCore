import uuid

from django.db import models
from simple_history.models import HistoricalRecords

from .core import Patient


class PatientAppointment(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="appointments")
    physician = models.ForeignKey(
       "staff.StaffMember",
        on_delete=models.PROTECT,
        related_name="appointments",
        limit_choices_to={"role__name": "Doctor"}
    )
    department = models.ForeignKey(
        "staff.Department",
        on_delete=models.PROTECT,
        related_name="appointment_department",
        limit_choices_to={"department_type": "CLINICAL"},
        null=True
    )
    appointment_date = models.DateField()
    appointment_time = models.TimeField()
    duration_minutes = models.PositiveIntegerField(default=30)
    reason = models.CharField(max_length=255)
    category = models.CharField(max_length=100)
    status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES, default="pending"
    )
    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(
        "staff.StaffMember", on_delete=models.SET_NULL, null=True, related_name="created_appointments"
    )
    modified_by = models.ForeignKey(
        "staff.StaffMember", on_delete=models.SET_NULL, null=True, related_name="modified_appointments"
    )
    last_modified = models.DateTimeField(auto_now=True)
    is_recurring = models.BooleanField(default=False)
    recurrence_pattern = models.CharField(
        max_length=50,
        choices=[("Daily", "Daily"), ("Weekly", "Weekly"), ("Monthly", "Monthly")],
        blank=True,
        null=True
    )
    start_time = models.DateTimeField(null=True)
    end_time = models.DateTimeField(null=True)
    history = HistoricalRecords(user_model="staff.StaffMember")

    class Meta:
        db_table = "patient_appointments"
        indexes = [
            models.Index(fields=["appointment_date", "appointment_time"]),
            models.Index(fields=["status", "appointment_date"]),
        ]
        constraints = [
            models.CheckConstraint(check=models.Q(end_time__gt=models.F("start_time")), name="valid_time_range"),
            models.UniqueConstraint(
                fields=["physician", "start_time"],
                name="unique_appointment_per_doctor_start_time"
            ),
        ]


    def __str__(self):
        return f"Appointment on {self.appointment_date} at {self.appointment_time} for {self.patient}"
