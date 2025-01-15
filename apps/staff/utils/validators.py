
from django.core.exceptions import ValidationError


def validate_working_hours(data):
    """Validate working hours and scheduling constraints."""
    if data.get("scheduled_hours", 0) > data.get("max_weekly_hours", 40):
        raise ValidationError("Scheduled hours exceed maximum weekly hours.")

def validate_department_transfer(data):
    """Validate department transfer requirements."""
    if not data.get("handover_documents"):
        raise ValidationError("Handover documentation is required for transfers.")
