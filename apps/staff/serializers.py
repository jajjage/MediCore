from django.contrib.auth.models import Permission
from django.db import transaction
from rest_framework import serializers

from .models import (
    Department,
    DepartmentMember,
    DoctorProfile,
    NurseProfile,
    StaffMember,
    StaffRole,
    StaffTransfer,
    TechnicianProfile,
    WorkloadAssignment,
)
from .utils.validators import validate_department_transfer, validate_working_hours


class DepartmentSerializer(serializers.ModelSerializer):
    staff_count = serializers.SerializerMethodField()
    active_staff_count = serializers.SerializerMethodField()
    sub_departments = serializers.SerializerMethodField()
    is_clinical = serializers.BooleanField(read_only=True)
    full_hierarchy_name = serializers.CharField(read_only=True)
    hospital = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Department
        fields = ["id", "name", "code", "department_type", "parent_department",
                 "hospital", "description", "location", "contact_email",
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

class DoctorProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorProfile
        fields = ["id", "qualification", "years_of_experience",
                 "certification_number", "specialty_notes", "specialization",
                 "license_number", "availability", "consulting_fee",
                 "max_patients_per_day"]
        read_only_fields = ["id"]

class NurseProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = NurseProfile
        fields = ["id", "qualification", "years_of_experience",
                 "certification_number", "specialty_notes", "nurse_license",
                 "ward_specialty", "shift_preferences"]
        read_only_fields = ["id"]

class TechnicianProfileSerializer(serializers.ModelSerializer):
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

class StaffTransferSerializer(serializers.ModelSerializer):
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

class StaffRoleSerializer(serializers.ModelSerializer):
    staff_count = serializers.SerializerMethodField()
    permissions = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Permission.objects.all()
    )

    class Meta:
        model = StaffRole
        fields = ["id", "name", "code", "permissions", "description",
                 "category", "is_active", "staff_count"]

    def validate(self, data):
        if data.get("category") == "MEDICAL" and not data.get("permissions").filter(
            codename__startswith="medical_"
        ).exists():
            raise serializers.ValidationError(
                "Medical staff roles must have medical permissions"
            )
        return data
    def get_staff_count(self, obj):
        return obj.get_staff_count()
class DepartmentMemberSerializer(serializers.ModelSerializer):
    workload = WorkloadAssignmentSerializer(many=True, read_only=True)
    transfers = StaffTransferSerializer(many=True, read_only=True)
    # schedule_conflicts = serializers.SerializerMethodField()

    class Meta:
        model = DepartmentMember
        fields = ["id", "department", "user", "role", "start_date", "end_date",
                 "is_primary", "assignment_type", "time_allocation",
                 "schedule_pattern", "workload", "transfers"]

    def validate(self, data):
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

    def _has_schedule_conflict(self, data):
        # Implementation of schedule conflict checking
        schedule = data.get("schedule_pattern", {})
        existing_schedules = DepartmentMember.objects.filter(
            department=data["department"],
            is_active=True
        ).exclude(id=self.instance.id if self.instance else None)

        # schedule conflict detection logic here
        for existing in existing_schedules:
            existing_schedule = existing.schedule_pattern
            # Check for overlapping days and times
            for day, time_slots in schedule.items():
                if day in existing_schedule:
                    existing_slots = existing_schedule[day]
                    # Check for time slot overlaps
                    for time_slot in time_slots:
                        start_time = time_slot.get("start")
                        end_time = time_slot.get("end")
                    for existing_slot in existing_slots:
                        existing_start = existing_slot.get("start")
                        existing_end = existing_slot.get("end")
                        # Check if time slots overlap
                        if (start_time < existing_end and end_time > existing_start):
                            return True
        return False

    def _check_department_capacity(self, data):
        department = data["department"]
        current_staff = department.staff_members.filter(is_active=True).count()

        # Get department's max capacity (implement this in Department model)
        max_capacity = department.max_staff_capacity
        if max_capacity:
            # Check if adding a new staff member would exceed capacity
            return current_staff < max_capacity
        return True

class StaffMemberSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    role_permissions = serializers.SerializerMethodField()
    departments = serializers.SerializerMethodField()
    current_roles = serializers.SerializerMethodField()
    primary_department = serializers.SerializerMethodField()
    department_memberships = DepartmentMemberSerializer(many=True, read_only=True)
    # staff_profile = serializers.SerializerMethodField()
    doctor_profile = DoctorProfileSerializer(required=False)

    class Meta:
        model = StaffMember
        fields = ["id", "email", "hospital", "first_name", "last_name",
                 "full_name", "role", "is_active", "role_permissions",
                 "departments", "current_roles", "primary_department",
                 "department_memberships", "doctor_profile"]
        read_only_fields = ["id", "role_permissions", "departments",
                           "current_roles", "primary_department", "doctor_profile"]

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"

    def get_role_permissions(self, obj):
        return [
            {
                "codename": perm.codename,
                "name": perm.name
            } for perm in obj.get_role_permissions()
        ]

    def get_departments(self, obj):
        return DepartmentSerializer(
            obj.get_all_departments(),
            many=True,
            context=self.context
        ).data

    def get_current_roles(self, obj):
        return list(obj.get_current_roles())

    def get_primary_department(self, obj):
        primary = obj.primary_department
        if primary:
            return DepartmentSerializer(primary.department).data
        return None

    # def get_staff_profile(self, obj):
    #     profile = obj.staff_profile
    #     if not profile:
    #         return None

    #     if isinstance(profile, DoctorProfile):
    #         return DoctorProfileSerializer(profile).data
    #     if isinstance(profile, NurseProfile):
    #         return NurseProfileSerializer(profile).data
    #     if isinstance(profile, TechnicianProfile):
    #         return TechnicianProfileSerializer(profile).data
    #     return None

    def validate(self, data):
        # Validate required fields
        if not data.get("email"):
            raise serializers.ValidationError("Email is required")
        if not data.get("first_name") or not data.get("last_name"):
            raise serializers.ValidationError(
                "Both first name and last name are required"
            )
        return data

    @transaction.atomic
    def create(self, validated_data):
        doctorprofile = validated_data.pop("doctor_profile", {})
        staff_member = StaffMember.objects.create(**validated_data)
        DoctorProfile.objects.create(staff_member=staff_member, **doctorprofile)

        return staff_member
