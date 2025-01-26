from datetime import datetime

from django.conf import settings
from django.db import models
from django.utils import timezone

from .core import PatientBasemodel


class PatientAppointment(PatientBasemodel):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]
    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.PROTECT,
        related_name="appointments"
    )
    physician = models.ForeignKey(
       "staff.DoctorProfile",
        on_delete=models.PROTECT,
        related_name="appointments",
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
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="created_appointments"
    )
    modified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="modified_appointments"
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


    class Meta:
        db_table = "patient_appointments"
        indexes = [
            models.Index(fields=["appointment_date", "appointment_time"]),
            models.Index(fields=["status", "appointment_date"]),
        ]
        constraints = [
            models.CheckConstraint(check=models.Q(end_time__gt=models.F("start_time")), name="valid_time_range")
        ]


    def __str__(self):
        return f"Appointment on {self.appointment_date} at {self.appointment_time} for {self.patient}"


    @classmethod
    def can_create_appointment(cls, patient_id, appointment_date, appointment_time):
        """
        Validate if a new appointment can be created for a patient.

        Args:
            patient_id: ID of the patient.
            appointment_date: Date of proposed appointment
            appointment_time: Time of proposed appointment

        Returns:
            dict: {'allowed': boolean, 'message': string}

        """
        try:
            # Convert strings to proper date/time objects if needed
            if isinstance(appointment_date, str):
                appointment_date = datetime.strptime(appointment_date, "%Y-%m-%d%z").date()
            if isinstance(appointment_time, str):
                appointment_time = datetime.strptime(appointment_time, "%H:%M%z").time()

            # Create datetime for comparison
            proposed_datetime = timezone.datetime.combine(
                appointment_date,
                appointment_time,
                tzinfo=timezone.get_current_timezone()
            )

            # Check if appointment is in the past
            if proposed_datetime < timezone.now():
                return {
                    "allowed": False,
                    "message": "Cannot create appointments in the past"
                }

            # Check for existing active appointments
            existing_appointments = cls.objects.filter(
                patient_id=patient_id,
                status__in=["pending", "approved"],
                appointment_date__gte=timezone.now().date()
            )

            if existing_appointments.exists():
                # Get details of existing appointments for error message
                active_appointments = []
                for apt in existing_appointments:
                    apt_datetime = timezone.datetime.combine(
                        apt.appointment_date,
                        apt.appointment_time,
                        tzinfo=timezone.get_current_timezone()
                    )
                    if apt_datetime >= timezone.now():
                        active_appointments.append(
                            f"{apt.appointment_date} at {apt.appointment_time}"
                        )

                if active_appointments:
                    return {
                        "allowed": False,
                        "message": (
                            "Patient has existing active appointments on: "
                            f"{', '.join(active_appointments)}. "
                            "Please cancel existing appointments before creating a new one."
                        )
                    }

            return {"allowed": True, "message": "Appointment can be created"}

        except (ValueError, TypeError) as e:
            return {
                "allowed": False,
                "message": f"Validation error: {e!s}"
            }
