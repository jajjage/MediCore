from django.db import models


class WorkloadAssignment(models.Model):
    department_member = models.ForeignKey("DepartmentMember", on_delete=models.PROTECT)
    week_start_date = models.DateField()
    scheduled_hours = models.DecimalField(max_digits=5, decimal_places=2)  # Example: up to 999.99 hours
    actual_hours = models.DecimalField(max_digits=5, decimal_places=2)
    on_call_hours = models.DecimalField(max_digits=5, decimal_places=2)
    notes = models.TextField()
    break_duration = models.DurationField(null=True, blank=True)
    is_overtime = models.BooleanField(default=False)
    shift_type = models.CharField(
        max_length=20,
        choices=[
            ("REGULAR", "Regular"),
            ("ON_CALL", "On Call"),
            ("EMERGENCY", "Emergency"),
        ],
    )
