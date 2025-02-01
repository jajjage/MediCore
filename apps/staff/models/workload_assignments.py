from django.conf import settings
from django.db import models


class WorkloadAssignment(models.Model):
    generated_shift = models.OneToOneField(
        "scheduling.GeneratedShift",
        on_delete=models.PROTECT,
        related_name="workload"
    )
    actual_start = models.DateTimeField(null=True, blank=True)
    actual_end = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    break_duration = models.DurationField(null=True, blank=True)
    is_overtime = models.BooleanField(default=False)
    status = models.CharField(
        max_length=20,
        choices=[
            ("COMPLETED", "Completed"),
            ("PARTIAL", "Partially Completed"),
            ("MISSED", "Missed"),
            ("OVERTIME", "Extended Beyond Shift")
        ],
        default="COMPLETED"
    )
    replacement_staff = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="covered_shifts"
    )

    class Meta:
        db_table = "workload_assignments"
        constraints = [
            models.CheckConstraint(
                check=models.Q(actual_start__lte=models.F("actual_end")),
                name="valid_assignment_duration"
            )
        ]
