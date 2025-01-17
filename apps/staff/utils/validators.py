
from django.core.exceptions import ValidationError


def validate_working_hours(data):
    """Validate working hours and scheduling constraints."""
    if data.get("scheduled_hours", 0) > data.get("max_weekly_hours", 40):
        raise ValidationError("Scheduled hours exceed maximum weekly hours.")

def validate_department_transfer(data):
    """Validate department transfer requirements."""
    if not data.get("handover_documents"):
        raise ValidationError("Handover documentation is required for transfers.")


def validate_schedule_pattern(value):
    if not isinstance(value, dict):
        raise ValidationError("Schedule pattern must be a dictionary.")

    for day, slots in value.items():
        if not isinstance(slots, list):
            raise ValidationError(f"Slots for {day} must be a list.")
        for slot in slots:
            if not all(k in slot for k in ("start", "end")):
                raise ValidationError(f"Each slot for {day} must have 'start' and 'end' keys.")
