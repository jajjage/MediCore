import uuid
from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers

from apps.staff.models import Department

from .models import (
    GeneratedShift,
    NurseAvailability,
    ShiftSwapRequest,
    ShiftTemplate,
    UserShiftPreference,
)

MAX_MONTH = 12
TIME_WINDOW_LENGTH = 2
MAX_HOUR = 23
MAX_MINUTE = 59
TIME_STRING_LENGTH = 5

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ["id", "email", "first_name", "last_name"]
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
    user = UserSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=get_user_model().objects.all(),
        write_only=True,
        source="user"
    )

    class Meta:
        model = NurseAvailability
        fields = [
            "id",
            "user",
            "user_id",
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

class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ["id", "name"]
class UserShiftPreferenceSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=get_user_model().objects.all(),
        write_only=True,
        source="user"
    )
    department = DepartmentSerializer(read_only=True)
    department_id = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(),
        write_only=True,
        source="department"
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
            "user_id",
            "department",
            "department_id",
            "preferred_shift_types",
            "preferred_shift_type_ids",
        ]
        read_only_fields = ["id"]

    def create(self, validated_data):
        # Extract M2M relationships
        preferred_shift_types = validated_data.pop("preferred_shift_types", [])

        # Set the current user if not provided
        if "user" not in validated_data:
            validated_data["user"] = self.context["request"].user

        # Create the instance
        instance = UserShiftPreference.objects.create(**validated_data)

        # Set M2M relationships
        instance.preferred_shift_types.set(preferred_shift_types)

        return instance

    def update(self, instance, validated_data):
        # Extract M2M relationships
        preferred_shift_types = validated_data.pop("preferred_shift_types", None)

        # Update the instance fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update M2M relationships if provided
        if preferred_shift_types is not None:
            instance.preferred_shift_types.set(preferred_shift_types)

        return instance
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

