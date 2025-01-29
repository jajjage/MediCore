from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone
from rest_framework import serializers

from apps.patients.mixins.patients_mixins import CalculationMixin
from core.models import MyUser

from .models import (
    Department,
    DepartmentMember,
    DoctorProfile,
    NurseProfile,
    StaffTransfer,
    TechnicianProfile,
    WorkloadAssignment,
)
from .utils.validators import validate_department_transfer, validate_working_hours

User = get_user_model()
class DepartmentSerializer(serializers.ModelSerializer):
    staff_count = serializers.SerializerMethodField()
    active_staff_count = serializers.SerializerMethodField()
    sub_departments = serializers.SerializerMethodField()
    is_clinical = serializers.BooleanField(read_only=True)
    full_hierarchy_name = serializers.CharField(read_only=True)

    class Meta:
        model = Department
        fields = ["id", "name", "code", "department_type", "parent_department",
                "description", "location", "contact_email",
                 "contact_phone", "department_head", "is_active", "created_at",
                 "updated_at", "staff_count", "active_staff_count",
                 "sub_departments", "is_clinical", "full_hierarchy_name"]
        read_only_fields = ["created_at", "updated_at"]

    def get_staff_count(self, obj):
        return obj.get_staff_count()

    def get_active_staff_count(self, obj):
        return obj.get_active_staff().count()

    def get_sub_departments(self, obj):
        return DepartmentSerializer(obj.get_sub_departments(), many=True).data

class DoctorProfileSerializer(serializers.ModelSerializer, CalculationMixin):
    full_name = serializers.SerializerMethodField()
    class Meta:
        model = DoctorProfile
        fields = ["id", "full_name", "qualification", "years_of_experience",
                 "certification_number", "specialty_notes", "specialization",
                 "license_number", "availability", "consulting_fee",
                 "max_patients_per_day"]
        read_only_fields = ["id"]

    def get_full_name(self, obj):
        return self.format_full_name(obj.user.first_name, obj.user.middle_name, obj.user.last_name)


class NurseProfileSerializer(serializers.ModelSerializer, CalculationMixin):
    class Meta:
        model = NurseProfile
        fields = ["id", "qualification", "years_of_experience",
                 "certification_number", "specialty_notes", "nurse_license",
                 "ward_specialty", "shift_preferences"]
        read_only_fields = ["id"]

class TechnicianProfileSerializer(serializers.ModelSerializer, CalculationMixin):
    class Meta:
        model = TechnicianProfile
        fields = ["id", "qualification", "years_of_experience",
                 "certification_number", "specialty_notes", "technician_license",
                 "equipment_specialties", "lab_certifications"]
        read_only_fields = ["id"]

class WorkloadAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkloadAssignment
        fields = ["department_member", "week_start_date", "scheduled_hours",
                 "actual_hours", "on_call_hours", "notes"]

    def validate(self, data):
        validate_working_hours(data)
        return data

class StaffTransferSerializer(serializers.ModelSerializer, CalculationMixin):
    handover_status = serializers.SerializerMethodField()

    class Meta:
        model = StaffTransfer
        fields = ["from_assignment", "to_assignment", "transfer_type",
                 "reason", "effective_date", "end_date", "approved_by",
                 "handover_status"]

    def validate(self, data):
        validate_department_transfer(data)
        return data


    def get_handover_status(self, obj):
        return {
            "documents_submitted": bool(obj.handover_documents),
            "pending_items": self._get_pending_items(obj)
        }

    def _get_pending_items(self, obj):
        required_docs = {"checklist", "knowledge_transfer", "resource_list"}
        submitted_docs = set(obj.handover_documents.keys())
        return list(required_docs - submitted_docs)


class DepartmentMemberSerializer(serializers.ModelSerializer):
    workload = WorkloadAssignmentSerializer(many=True, read_only=True)
    transfers = StaffTransferSerializer(many=True, read_only=True)
    user = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),  # We'll set this in __init__
        required=True
    )

    class Meta:
        model = DepartmentMember
        fields = ["id", "department", "user", "role", "start_date", "end_date",
                 "is_primary", "assignment_type", "time_allocation", "emergency_contact",
                 "schedule_pattern", "workload", "transfers", "is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request and hasattr(request, "tenant") and hasattr(request.tenant, "hospital_profile"):
            current_hospital = request.tenant.hospital_profile
            print(current_hospital)
            # Filter users who have active membership with current hospital
            valid_users = User.objects.filter(
                hospital_memberships_user__hospital_profile=current_hospital,
                hospital_memberships_user__is_active=True,
            ).distinct()
            self.fields["user"].queryset = valid_users

    def validate(self, data):
        # Validate user has active membership
        if not self._validate_hospital_membership(data["user"]):
            raise serializers.ValidationError(
                "User does not have an active membership with this hospital"
            )

        # Validate schedule conflicts
        if self._has_schedule_conflict(data):
            raise serializers.ValidationError(
                "Schedule conflict detected with existing assignments"
            )

        # Validate department capacity
        if not self._check_department_capacity(data):
            raise serializers.ValidationError(
                "Department has reached maximum staff capacity"
            )

        return data

    def _validate_hospital_membership(self, user):
        request = self.context.get("request")
        if not request:
            return False

        current_hospital = request.tenant.hospital_profile
        return user.hospital_memberships_user.filter(
            hospital=current_hospital,
            is_active=True,
            end_date__gte=timezone.now().date(),
        ).exists()

    def _has_schedule_conflict(self, data):
        new_schedule = data.get("schedule_pattern", {})
        existing_schedules = DepartmentMember.objects.filter(
            department=data["department"],
            is_active=True
        ).exclude(id=self.instance.id if self.instance else None)

        for existing in existing_schedules:
            existing_schedule = existing.schedule_pattern or {}
            for day, new_time_slots in new_schedule.items():
                if day in existing_schedule:
                    existing_time_slots = existing_schedule[day]
                    for new_slot in new_time_slots:
                        new_start = new_slot.get("start")
                        new_end = new_slot.get("end")
                        for existing_slot in existing_time_slots:
                            existing_start = existing_slot.get("start")
                            existing_end = existing_slot.get("end")
                            if new_start < existing_end and new_end > existing_start:
                                return True
        return False

    def _check_department_capacity(self, data):
        department = data["department"]
        current_staff = department.staff_members.filter(is_active=True).count()

        # Ensure max_staff_capacity exists and handle None
        max_capacity = getattr(department, "max_staff_capacity", None)
        if max_capacity is not None:
            return current_staff < max_capacity  # Allow if under capacity
        return True  # No capacity limit means always valid
