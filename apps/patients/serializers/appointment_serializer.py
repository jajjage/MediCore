from django.utils import timezone
from rest_framework import serializers

from apps.patients.mixins.patients_mixins import (
    AppointmentValidator,
    CalculationMixin,
)
from apps.patients.models import (
    PatientAppointment,
)
from apps.staff.models.department_member import DepartmentMember
from hospital.models.hospital_members import HospitalMembership

from .base_serializer import BasePatientSerializer


class PatientAppointmentCreateSerializer(BasePatientSerializer, CalculationMixin):
    user = serializers.UUIDField(write_only=True)  # For accepting UUID in request
    department = serializers.UUIDField(write_only=True)
    class Meta:
        model = PatientAppointment
        fields = [
            "id",
            "user",
            "department",
            "appointment_date",
            "appointment_time",
            "duration_minutes",
            "reason",
            "category",
            "status",
            "notes",
            "start_time",
            "end_time",
            "is_recurring",
            "recurrence_pattern",
        ]
        read_only_fields = [
            "id",
            "created_by",
            "modified_by",
            "last_modified",
            "patient",
        ]

    def validate(self, data):
        # Validate recurring appointment settings
        department_uuid = data.get("department")
        user_uuid = data.get("user")
        request = self.context.get("request")

        if not request or not hasattr(request, "tenant") or not hasattr(request.tenant, "hospital_profile"):
            raise serializers.ValidationError("Invalid tenant configuration")

        current_hospital = request.tenant.hospital_profile

        # Validate and get user
        try:
            # Find user through their hospital membership
            membership = HospitalMembership.objects.get(
                user__id=user_uuid,
                hospital_profile=current_hospital,
                is_active=True,
            )
            physician = membership.user
        except HospitalMembership.DoesNotExist:
            raise serializers.ValidationError(
                f"User with ID {user_uuid} does not have an active membership in this hospital"
            )

        if department_uuid and physician and not DepartmentMember.objects.filter(
            department_id=department_uuid,
            user_id=user_uuid,
            role="DOCTOR"
        ).exists():
                raise serializers.ValidationError({
                    "physician": "Selected physician does not belong to the specified department."
                })

        AppointmentValidator.validate_recurrence(
            data.get("is_recurring"),
            data.get("recurrence_pattern")
        )

        # Validate appointment datetime
        appointment_date = data.get("appointment_date",
                                 getattr(self.instance, "appointment_date", None))
        appointment_time = data.get("appointment_time",
                                 getattr(self.instance, "appointment_time", None))

        AppointmentValidator.validate_appointment_datetime(
            appointment_date,
            appointment_time,
            self.instance
        )

        # Validate time slot availability
        AppointmentValidator.validate_time_slot(
            appointment_date,
            appointment_time,
            physician,
            self.instance
        )
        return data

class PatientAppointmentSerializer(BasePatientSerializer, CalculationMixin):
    physician_full_name = serializers.SerializerMethodField()
    patient_full_name = serializers.SerializerMethodField()
    department_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    modified_by_name = serializers.SerializerMethodField()
    current_prescription = serializers.SerializerMethodField()

    class Meta:
        model = PatientAppointment
        fields = [
            "id",
            "patient_full_name",
            "physician_full_name",
            "department_name",
            "appointment_date",
            "appointment_time",
            "duration_minutes",
            "reason",
            "category",
            "status",
            "notes",
            "start_time",
            "end_time",
            "is_recurring",
            "recurrence_pattern",
            "created_by",
            "created_by_name",
            "modified_by",
            "modified_by_name",
            "last_modified",
            "current_prescription",
        ]

    def get_physician_full_name(self, obj):
        return self.physician_format_full_name(
            obj.physician.first_name,
            obj.physician.last_name
        )

    def get_patient_full_name(self, obj):
        return self.format_full_name(
            obj.patient.first_name,
            obj.patient.middle_name,
            obj.patient.last_name
        )

    def get_department_name(self, obj):
        return obj.department.name if obj.department else None

    def get_created_by_name(self, obj):
        if obj.created_by:
            return f"{obj.created_by.first_name} {obj.created_by.last_name}"
        return None

    def get_modified_by_name(self, obj):
        if obj.modified_by:
            return f"{obj.modified_by.first_name} {obj.modified_by.last_name}"
        return None

    def get_current_prescription(self, obj):
        prescription = getattr(obj, "prescription", None)
        if prescription:
            return {
                "id": prescription.id,
                "medicines": prescription.medicines,
                "instructions": prescription.instructions,
                "issued_date": prescription.issued_date,
                "valid_until": prescription.valid_until,
            }
        return None


class AvailabilityCheckSerializer(serializers.Serializer):
    physician_id = serializers.UUIDField()
    start_datetime = serializers.DateTimeField()
    end_datetime = serializers.DateTimeField()
    department_id = serializers.UUIDField(required=False)

    def validate(self, data):
        if data["start_datetime"] >= data["end_datetime"]:
            raise serializers.ValidationError(
                "End datetime must be after start datetime"
            )

        if data["start_datetime"] < timezone.now():
            raise serializers.ValidationError(
                "Start datetime cannot be in the past"
            )

        return data

class TimeSlotSerializer(serializers.Serializer):
    start_time = serializers.DateTimeField()
    end_time = serializers.DateTimeField()
    is_available = serializers.BooleanField()
    conflicting_appointment = serializers.UUIDField(allow_null=True)


class RecurringAppointmentSerializer(serializers.ModelSerializer):
    recurrence_pattern = serializers.ChoiceField(
        choices=["daily", "weekly", "monthly"],
        required=True
    )
    frequency = serializers.IntegerField(
        min_value=1,
        required=True,
        help_text="How often the appointment repeats (e.g., every 2 weeks)"
    )
    start_date = serializers.DateField(required=True)
    end_date = serializers.DateField(required=True)
    appointment_time = serializers.TimeField(required=True)
    duration = serializers.IntegerField(
        min_value=15,
        required=True,
        help_text="Duration in minutes"
    )
    physician_id = serializers.UUIDField(required=True)
    department_id = serializers.UUIDField(required=True)
    notes = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = PatientAppointment
        fields = [
            "recurrence_pattern",
            "frequency",
            "start_date",
            "end_date",
            "appointment_time",
            "duration",
            "physician_id",
            "department_id",
            "notes"
        ]

    def validate(self, data):
        if data["start_date"] > data["end_date"]:
            raise serializers.ValidationError(
                "End date must be after start date"
            )
        if data["start_date"] < timezone.now().date():
            raise serializers.ValidationError(
                "Start date cannot be in the past"
            )
        return data


class AppointmentStatusUpdateSerializer(serializers.ModelSerializer):
    status = serializers.ChoiceField(
        choices=[
            "pending",
            "approved",
            "checked_in",
            "in_progress",
            "completed",
            "cancelled",
            "no_show",
            "rejected"
        ]
    )
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=500
    )

    class Meta:
        model = PatientAppointment
        fields = ["status", "notes"]

    def validate_status(self, value):
        instance = self.instance
        if instance:
            if instance.status in ["completed", "cancelled", "rejected"]:
                raise serializers.ValidationError(
                    f"Cannot update status of {instance.status} appointment"
                )
            if instance.status == "no_show" and value not in ["cancelled", "completed"]:
                raise serializers.ValidationError(
                    "No-show appointments can only be marked as cancelled or completed"
                )
        return value
