import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.staff.models import Department, DepartmentMember

from .managers import DepartmentMemberShiftManager, ShiftQuerySet


class ShiftTemplate(models.Model):
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
    role_requirement = models.CharField(
        max_length=30,
        choices=DepartmentMember.ROLE_TYPES,
        default="DOCTOR"
    )
    max_staff = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "shift_templates"
        ordering = ["valid_from", "start_time"]


    def __str__(self):
        return f"{self.department} - {self.name}"


class DepartmentMemberShift(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    department_member = models.ForeignKey(
        DepartmentMember,
        on_delete=models.CASCADE,
        related_name="assigned_shifts"
    )
    shift_template = models.ForeignKey(
        ShiftTemplate,
        on_delete=models.CASCADE
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


class GeneratedShift(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = "SCHEDULED", _("Scheduled")
        COMPLETED = "COMPLETED", _("Completed")
        CANCELLED = "CANCELLED", _("Cancelled")
        EMERGENCY = "EMERGENCY", _("Emergency")

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
    geo_location = models.CharField(
        max_length=100,
        blank=True,
        help_text="Location tag for distributed facilities"
    )
    required_equipment = models.JSONField(
        default=list,
        blank=True,
        help_text="Equipment needed for this shift"
    )
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
    # Added to GeneratedShift model
    prioritization = models.CharField(
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

    objects = models.Manager()
    active = models.Manager.from_queryset(ShiftQuerySet)()


    class Meta:
        db_table = "generated_shifts"
        ordering = ["start_datetime"]
        indexes = [
            models.Index(fields=["start_datetime", "end_datetime"])
        ]



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
        related_name="swap_requests"
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

    class Meta:
        db_table = "shift_swap_requests"
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
