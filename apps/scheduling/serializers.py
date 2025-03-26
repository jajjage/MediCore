import uuid
from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers

from .models import (
    GeneratedShift,
    NurseAvailability,
    ShiftSwapRequest,
    ShiftTemplate,
    UserShiftPreference,
)

MAX_MONTH = 12
User = get_user_model()
class ShiftTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShiftTemplate
        fields = [
            "id", "department", "name", "start_time", "end_time", "rotation_group",
            "recurrence", "recurrence_parameters", "valid_from", "valid_until", "is_weekend",
            "required_role", "required_skill", "max_staff", "is_active", "max_consecutive_weeks",
            "max_staff_weekday", "max_staff_weekend", "cooldown_weeks"
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

class ShiftSwapRequestSerializer(serializers.ModelSerializer):
    original_shift = serializers.PrimaryKeyRelatedField(queryset=GeneratedShift.objects.filter(status="SCHEDULED"))
    proposed_shift = serializers.PrimaryKeyRelatedField(queryset=GeneratedShift.objects.filter(status="SCHEDULED"), allow_null=True, required=False)
    requesting_user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    requested_user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), allow_null=True, required=False)

    class Meta:
        model = ShiftSwapRequest
        fields = (
            "id", "original_shift", "proposed_shift", "requesting_user", "requested_user",
            "status", "reason", "created_at", "expiration", "constraints"
        )
        read_only_fields = ("created_at",)

    def validate(self, attrs):
        # Basic validation: Ensure original_shift is provided.
        if not attrs.get("original_shift"):
            raise serializers.ValidationError("Original shift is required.")
        # Additional validations can be added here.
        return attrs

    def create(self, validated_data):
        # Create the swap request instance.
        swap_request = ShiftSwapRequest.objects.create(**validated_data)
        return swap_request

class NurseAvailabilitySerializer(serializers.ModelSerializer):
    user = serializers.SlugRelatedField(
        slug_field="email",
        queryset=get_user_model().objects.all(),
        required=False
    )

    class Meta:
        model = NurseAvailability
        fields = [
            "id",
            "user",
            "start_date",
            "end_date",
            "reason",
            "availability_status",
            "is_blackout"
        ]
        read_only_fields = ["id"]

    def validate(self, data):
        if data.get("end_date") and data.get("start_date") and data["end_date"] < data["start_date"]:
            raise serializers.ValidationError({
                "end_date": "End date must be after start date"
            })
        return data

    def create(self, validated_data):
        if "user" not in validated_data:
            validated_data["user"] = self.context["request"].user
        return super().create(validated_data)

class UserShiftPreferenceSerializer(serializers.ModelSerializer):
    user = serializers.SlugRelatedField(
        slug_field="username",
        queryset=get_user_model().objects.all(),
        required=False
    )
    preferred_shift_types = ShiftTemplateSerializer(many=True, read_only=True)
    preferred_shift_type_ids = serializers.PrimaryKeyRelatedField(
        source="preferred_shift_types",
        write_only=True,
        many=True,
        queryset=ShiftTemplate.objects.all(),
        required=False
    )

    class Meta:
        model = UserShiftPreference
        fields = [
            "id",
            "user",
            "department",
            "preferred_shift_types",
            "preferred_shift_type_ids",
            "availability"
        ]
        read_only_fields = ["id"]

    def validate_availability(self, value):
        """
        Validate the availability JSON structure.

        Expected format: {
            "MONDAY": [["09:00", "17:00"]],
            "TUESDAY": [["09:00", "17:00"], ["18:00", "22:00"]],
            ...
        }
        """
        valid_days = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"]

        if not isinstance(value, dict):
            raise serializers.ValidationError("Availability must be a dictionary")

        for day, time_windows in value.items():
            if day not in valid_days:
                raise serializers.ValidationError(f"Invalid day: {day}")

            if not isinstance(time_windows, list):
                raise serializers.ValidationError(f"Time windows for {day} must be a list")

            SHIFT_WINDOW_LENGTH = 2
            for window in time_windows:
                if not isinstance(window, list) or len(window) != SHIFT_WINDOW_LENGTH:
                    raise serializers.ValidationError(
                        "Each time window must be a list of two time strings"
                    )

                try:
                    # Validate time format
                    from datetime import datetime
                    for time_str in window:
                        datetime.strptime(time_str, "%H:%M")
                except ValueError:
                    raise serializers.ValidationError(
                        f"Invalid time format in {day}: {window}. Use HH:MM format"
                    )

        return value

    def create(self, validated_data):
        if "user" not in validated_data:
            validated_data["user"] = self.context["request"].user
        return super().create(validated_data)


class ShiftGenerationSerializer(serializers.Serializer):
    department_id = serializers.CharField(
        required=True,
       help_text="Department ID as UUID or string"
    )
    year = serializers.IntegerField(
        required=True,
        min_value=2000,
        max_value=2100
    )
    month = serializers.IntegerField(
        required=True,
        min_value=1,
        max_value=12
    )

    schema_name = serializers.CharField(
        required=True,
        max_length=63
    )

    def validate(self, data):
        # Optional: Custom validation across multiple fields

        if data["month"] < 1 or data["month"] > MAX_MONTH:
            raise serializers.ValidationError("Invalid month")
        return data

    def validate_department_id(self, value):
        # Additional validation for UUID
        try:
            # Try to convert to UUID if it's a valid UUID string
            department_id = uuid.UUID(str(value))
            return str(department_id)
        except ValueError:
            # If not a valid UUID, you can add custom handling
            raise serializers.ValidationError("Invalid department ID format")

    def create(self, validated_data):
        # Call the Celery task with validated data
        from .tasks import generate_initial_shifts

        generate_initial_shifts.delay(
            department_id=validated_data["department_id"],
            year=validated_data["year"],
            month=validated_data["month"],
            schema_name=validated_data["schema_name"]
        )

        return validated_data
