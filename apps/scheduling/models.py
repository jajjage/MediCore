import uuid
from datetime import date, timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.staff.models import Department, DepartmentMember

from .managers import DepartmentMemberShiftManager, ShiftQuerySet


class ShiftTemplate(models.Model):
    MAX_CONSECUTIVE_WEEKS_CHOICES = [(i, i) for i in range(1, 5)]
    class Recurrence(models.TextChoices):
        DAILY = "DAILY", _("Daily")
        WEEKLY = "WEEKLY", _("Weekly")
        MONTHLY = "MONTHLY", _("Monthly")
        YEARLY = "YEARLY", _("Yearly")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name="shift_templates"
    )
    name = models.CharField(max_length=100)
    start_time = models.TimeField()
    end_time = models.TimeField()
    recurrence = models.CharField(
        max_length=10,
        choices=Recurrence.choices,
        default=Recurrence.WEEKLY
    )
    recurrence_parameters = models.JSONField(
        default=dict,
        help_text="e.g., {'interval': 1, 'days': ['MON', 'WED']}"
    )
    valid_from = models.DateField()
    valid_until = models.DateField(null=True, blank=True)
    required_role = models.CharField(
        max_length=30,
        choices=[("NURSE", "Nurse"), ("PART_TIME", "Part-Time"), ("STUDY", "Study Leave"), ("ANY", "Any")],
        default="ANY",
        help_text="Role required for this shift"
    )
    required_skill = models.CharField(
        max_length=50,
        choices=[("junior", "Junior"), ("senior", "Senior"), ("any", "Any")],
        default="any"
    )
    rotation_group = models.CharField(
        max_length=20,
        choices=[("MORNING", "Morning"), ("AFTERNOON", "Afternoon"), ("NIGHT", "Night")],
    )
    is_weekend = models.BooleanField(default=False)
    max_staff_weekday = models.PositiveIntegerField(default=1)
    max_staff_weekend = models.PositiveIntegerField(default=1)
    max_consecutive_weeks = models.PositiveIntegerField(
        choices=MAX_CONSECUTIVE_WEEKS_CHOICES,
        default=2
    )
    cooldown_weeks = models.PositiveIntegerField(default=4)
    min_shift_gap = models.DurationField(default=timedelta(hours=12))
    max_staff = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    penalty_weight = models.FloatField(default=1.0, help_text="Weight for soft constraint violations")
    class Meta:
        db_table = "shift_templates"
        ordering = ["valid_from", "start_time", "rotation_group"]

    def __str__(self):
        return f"{self.department} - {self.name}"

    # In ShiftTemplate model
    def clean(self):
        super().clean()
        if self.recurrence == "WEEKLY" and not self.recurrence_parameters.get("days"):
            raise ValidationError("Weekly recurrence requires 'days' parameter")

        if self.recurrence == "MONTHLY" and not any(
            key in self.recurrence_parameters
            for key in ["day_of_month", "weekday_position"]
        ):
            raise ValidationError("Monthly recurrence requires day specification")

        if self.valid_until and self.valid_from and self.valid_until < self.valid_from:
            raise ValidationError({"valid_until": "Template's end date cannot be before its start date."})

class DepartmentMemberShift(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    department_member = models.ForeignKey(
        DepartmentMember,
        on_delete=models.CASCADE,
        related_name="assigned_shifts",
        null=True
    )
    shift_template = models.ForeignKey(
        ShiftTemplate,
        on_delete=models.CASCADE,
        null=True
    )
    assignment_start = models.DateField()
    assignment_end = models.DateField(null=True, blank=True)
    max_weekly_occurrences = models.PositiveIntegerField(null=True, blank=True)

    objects = DepartmentMemberShiftManager()

    class Meta:
        db_table = "department_member_shifts"
        indexes = [
            models.Index(fields=["assignment_start", "assignment_end"])
        ]
    def clean(self):
        super().clean()
        if self.assignment_end and self.assignment_end < self.assignment_start:
            raise ValidationError({"assignment_end": "End date must be on or after the start date."})

class GeneratedShift(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = "SCHEDULED", _("Scheduled")
        COMPLETED = "COMPLETED", _("Completed")
        CANCELLED = "CANCELLED", _("Cancelled")
        EMERGENCY = "EMERGENCY", _("Emergency")
        SWAPPED = "SWAPPED", _("Swapped")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="generated_shifts"
    )
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    is_emergency_override = models.BooleanField(default=False)
    override_reason = models.TextField(blank=True)
    override_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="overridden_shifts"
    )
    source_template = models.ForeignKey(
        ShiftTemplate,
        on_delete=models.SET_NULL,
        null=True
    )
    priority = models.CharField(
        max_length=20,
        choices=[
            ("ROUTINE", "Routine Appointments"),
            ("URGENT", "Urgent Care"),
            ("PROCEDURE", "Procedure Blocks")
        ],
        default="ROUTINE"
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SCHEDULED
    )
    penalty_score = models.FloatField(default=0.0)

    objects = models.Manager()
    active = models.Manager.from_queryset(ShiftQuerySet)()


    class Meta:
        db_table = "generated_shifts"
        ordering = ["start_datetime"]
        indexes = [
            models.Index(fields=["start_datetime", "end_datetime"])
        ]
    def clean(self):
        super().clean()
        if self.start_datetime >= self.end_datetime:
            raise ValidationError("Start datetime must be before end datetime.")
class UserShiftState(models.Model):
    """
    Tracks the state of a user's shift rotation within a department, ensuring continuity when generating shifts incrementally.

    Attributes:
        user (ForeignKey): A reference to the user associated with this shift state.
        department (ForeignKey): The department in which the shift state applies.
        current_template (ForeignKey): The shift template currently in use.
        last_shift_end (DateTimeField): The end datetime of the user's most recent shift.
        rotation_index (IntegerField): The current position in the rotation cycle.
        consecutive_weeks (IntegerField): The count of consecutive weeks the user has been scheduled for shifts.
        cooldowns (JSONField): A dictionary that stores cooldown periods to control shift assignment frequency.
            Expected structure:
                Keys (str): Represent identifiers for the cooldown context (e.g., shift template identifiers or custom cooldown names).
                Values (dict): Each value contains details about a cooldown period and is expected to have the following keys:
                    "start" (str/datetime): The datetime when the cooldown period begins.
                    "end" (str/datetime): The datetime when the cooldown period expires.
            Note: The values may be adjusted as needed to fit specific business logic. By default, cooldowns is an empty dictionary.

    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey( settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="shift_state")
    department = models.ForeignKey("staff.Department", on_delete=models.CASCADE)
    current_template = models.ForeignKey("ShiftTemplate", on_delete=models.CASCADE)
    last_shift_end = models.DateTimeField()
    rotation_index = models.IntegerField(default=0)
    consecutive_weeks = models.IntegerField(default=0)
    cooldowns = models.JSONField(default=dict)

    class Meta:
        db_table = "nurse_shift_state"
        unique_together = ["user", "department"]

    def __str__(self):
        return f"{self.user.username} - {self.department.name} - {self.current_template.name}"

class ShiftSwapRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    original_shift = models.ForeignKey(
        "GeneratedShift",
        on_delete=models.CASCADE,
        related_name="swap_requests_as_original"
    )
    proposed_shift = models.ForeignKey(
        "GeneratedShift",
        on_delete=models.CASCADE,
        related_name="swap_requests_as_proposed"
    )
    requesting_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="swap_requesting_user"
    )
    requested_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="swap_requested_user"
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ("PENDING", "Pending Approval"),
            ("APPROVED", "Approved"),
            ("REJECTED", "Rejected")
        ],
        default="PENDING"
    )
    reason = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True, editable=False, null=True)
    expiration = models.DateTimeField(null=True)
    constraints = models.JSONField(default=dict)

    class Meta:
        db_table = "shift_swap_requests"
        indexes = [
            models.Index(fields=["expiration"])
        ]
        constraints = [
            # Simply enforce that original_shift_id is not null
            models.CheckConstraint(
                check=models.Q(original_shift_id__isnull=False),
                name="original_shift_must_exist"
            )
        ]


    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        if self.original_shift_id is None:
            raise ValidationError({
                "original_shift": "Original shift is required"
            })

        # If you need to check if the shift is scheduled, do it here
        if hasattr(self.original_shift, "status") and self.original_shift.status != "SCHEDULED":
            raise ValidationError({
                "original_shift": "Original shift must be in scheduled status"
            })


class NurseAvailability(models.Model):
    AVAILABILITY_CHOICES = [
        ("available", "Available"),
        ("unavailable", "Unavailable"),
        ("preferred_off", "Preferred Off"),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.CharField(max_length=100)  # Illness/Vacation/etc
    availability_status = models.CharField(max_length=20, choices=AVAILABILITY_CHOICES, default="available")
    is_blackout = models.BooleanField(default=True)

    class Meta:
        db_table = "nurse_availability"
        unique_together = ("user", "start_date")
        ordering = ["start_date", "end_date"]
        indexes = [
            models.Index(fields=["start_date", "end_date"])
        ]



class ShiftAssignmentHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    previous_state = models.CharField(max_length=20, choices=GeneratedShift.Status.choices)
    shift_assignment = models.ForeignKey(GeneratedShift, on_delete=models.CASCADE)
    new_state = models.CharField(max_length=20, choices=GeneratedShift.Status.choices)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                   help_text="The person responsible for this change")
    changed_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "nurse_shift_history"
        ordering = ["changed_at"]
        indexes = [
            models.Index(fields=["changed_at"])
        ]

class UserShiftPreference(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    preferred_shift_types = models.ManyToManyField(ShiftTemplate)
    availability = models.JSONField(default=dict)  # {day: [time_windows]}

    class Meta:
        db_table = "nurse_shift_preferences"
        unique_together = ["user", "department"]

    def __str__(self):
        return f"{self.user.username} - {self.department.name}"


class WeekendShiftPolicy(models.Model):
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    max_weekend_shifts = models.PositiveIntegerField(default=2)
    max_consecutive_weekends = models.PositiveIntegerField(default=2)
    max_weekend_shifts_per_quarter = models.PositiveIntegerField(default=8)

    class Meta:
        db_table = "weekend_shift_policy"
        unique_together = ["department"]

    def __str__(self):
        return f"{self.department.name} Weekend Shift Policy"

