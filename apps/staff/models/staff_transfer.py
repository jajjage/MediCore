
from django.conf import settings
from django.db import models


class StaffTransfer(models.Model):
    from_assignment = models.ForeignKey(
        "DepartmentMember",
        on_delete=models.CASCADE,
        related_name="transfers_out"
    )
    to_assignment = models.ForeignKey(
        "DepartmentMember",
        on_delete=models.CASCADE,
        related_name="transfers_in"
    )
    transfer_type = models.CharField(
        choices=[
            ("PERMANENT", "Permanent Transfer"),
            ("TEMPORARY", "Temporary Cover"),
            ("ROTATION", "Rotation"),
            ("EMERGENCY", "Emergency Reassignment")
        ]
    )
    reason = models.TextField()
    effective_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True)
    required_documents = models.JSONField(default=list)
    handover_checklist = models.JSONField(default=dict)
    notice_period = models.IntegerField(default=30)
    transition_notes = models.TextField(blank=True)
