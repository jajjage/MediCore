from datetime import datetime, timedelta

from django.utils import timezone
from rest_framework import serializers

from .models import ShiftTemplate


class ShiftTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShiftTemplate
        fields = [
            "id", "department", "name", "start_time", "end_time", "rotation_group",
            "recurrence", "recurrence_parameters", "valid_from", "valid_until",
            "role_requirement", "max_staff", "is_active", "max_consecutive_weeks"
        ]

    def validate(self, data):
        if data.get("start_time") and data.get("end_time"):
            start_time = data["start_time"]
            end_time = data["end_time"]

            # Convert times to timezone-aware datetime for comparison
            today = timezone.now().date()
            start_datetime = timezone.make_aware(
                datetime.combine(today, start_time)
            )
            end_datetime = timezone.make_aware(
                datetime.combine(today, end_time)
            )

            # If end time is before start time, assume it's the next day
            if end_time < start_time:
                end_datetime = end_datetime + timedelta(days=1)

            # Calculate shift duration in hours
            duration = (end_datetime - start_datetime).total_seconds() / 3600

            # Validate that shift is not longer than 24 hours
            if duration > 24:  # noqa: PLR2004
                raise serializers.ValidationError({
                    "end_time": "Shift duration cannot be longer than 24 hours"
                })

        # Validate that valid_until is after valid_from if provided
        if data.get("valid_until") and data.get("valid_from") and data["valid_until"] <= data["valid_from"]:
            raise serializers.ValidationError({
                "valid_until": "Valid until date must be after valid from date"
            })

        # Validate recurrence_parameters format based on recurrence type
        if data.get("recurrence") == "WEEKLY" and data.get("recurrence_parameters") and not isinstance(data["recurrence_parameters"].get("days"), list):
            raise serializers.ValidationError({
                "recurrence_parameters": "Weekly recurrence must include days list"
            })

        return data
