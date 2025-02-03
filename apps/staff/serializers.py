from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import serializers

from apps.patients.mixins.patients_mixins import CalculationMixin
from apps.scheduling.models import DepartmentMemberShift, ShiftTemplate
from apps.scheduling.utils.shift_generator import ShiftGenerator
from hospital.models.hospital_members import HospitalMembership

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
    shifts = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        write_only=True,
        help_text="List of shift assignments in format: "
                 "{shift_template: UUID, start_date: YYYY-MM-DD, end_date: YYYY-MM-DD}"
    )
    user = serializers.UUIDField(write_only=True)  # For accepting UUID in request
    user_details = serializers.SerializerMethodField(read_only=True)  # For returning user details
    department = serializers.UUIDField(write_only=True)
    class Meta:
        model = DepartmentMember
        fields = ["id", "department", "user", "user_details", "role", "start_date", "end_date",
                 "is_primary", "assignment_type", "time_allocation", "emergency_contact",
                 "workload", "transfers", "is_active", "shifts", "max_weekly_hours"]
        read_only_fields = ["id", "workload", "transfers"]
        extra_kwargs = {
            "user": {"required": True},
            "department": {"required": True}
        }

    def get_user_details(self, obj):
        return {
            "id": obj.user.id,
            "full_name": f"{obj.user.first_name} {obj.user.last_name}",
            "email": obj.user.email
        }

    def validate(self, data):
        """Validate the incoming data and ensure that the user and department are valid."""
        user_uuid = data.get("user")
        department_uuid = data.get("department")
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
            user = membership.user
        except HospitalMembership.DoesNotExist:
            raise serializers.ValidationError(
                f"User with ID {user_uuid} does not have an active membership in this hospital"
            )

        # Validate and get department
        try:
            department = Department.objects.get(
                id=department_uuid,
            )
        except Department.DoesNotExist:
            raise serializers.ValidationError(
                f"Department with ID {department_uuid} does not exist in this hospital"
            )

        # Check for existing department membership
        existing_membership = DepartmentMember.objects.filter(
            user=user,
            department=department,
            is_active=True
        ).exists()

        if existing_membership:
            raise serializers.ValidationError(
                "User already has an active membership in this department"
            )

        # Replace UUIDs with actual model instances
        data["user"] = user
        data["department"] = department
        shifts = data.pop("shifts", [])
        member = DepartmentMember(**data)
        self._validate_shifts(shifts, data["department"])
        self._validate_max_hourly(shifts, member)
        data["_shifts"] = shifts

        # Validate department capacity
        if not self._check_department_capacity(data):
            raise serializers.ValidationError(
                "Department has reached maximum staff capacity"
            )
        # print(data)

        return data

    def _validate_shifts(self, shifts, department):
        for shift in shifts:
            template_id = shift.get("shift_template")
            # Validate dates
            try:
                if "start_date" in shift:
                    parse_date(shift["start_date"])
                if "end_date" in shift:
                    parse_date(shift["end_date"])
            except ValueError:
                raise serializers.ValidationError("Invalid date format. Use YYYY-MM-DD")

            try:
                template = ShiftTemplate.objects.get(
                    id=template_id,
                    department=department
                )
                if template.role_requirement != self.initial_data.get("role"):
                    raise serializers.ValidationError(
                        f"Shift template {template_id} requires {template.role_requirement} role"
                    )
            except ShiftTemplate.DoesNotExist:
                raise serializers.ValidationError(
                    f"Invalid shift template ID: {template_id} for this department"
                )


    def _check_department_capacity(self, data):
        print("emergency")
        department = data["department"]
        current_staff = department.department_members.filter(is_active=True).count()

        # Ensure max_staff_capacity exists and handle None
        max_capacity = getattr(department, "max_staff_capacity", None)
        if max_capacity is not None:
            return current_staff < max_capacity  # Allow if under capacity
        return True  # No capacity limit means always valid

    def create(self, validated_data):
        # First ensure we have proper model instances
        if isinstance(validated_data.get("user"), dict):
            user_id = validated_data["user"].get("id")
            validated_data["user"] = User.objects.get(id=user_id)

        if isinstance(validated_data.get("department"), dict):
            dept_id = validated_data["department"].get("id")
            validated_data["department"] = Department.objects.get(id=dept_id)

        # Get shifts data before creating member
        shifts = validated_data.pop("_shifts", [])

        try:
            # Create the department member
            member = DepartmentMember.objects.create(
                user=validated_data["user"],
                department=validated_data["department"],
                role=validated_data.get("role"),
                start_date=validated_data.get("start_date"),
                end_date=validated_data.get("end_date"),
                is_primary=validated_data.get("is_primary", False),
                assignment_type=validated_data.get("assignment_type"),
                time_allocation=validated_data.get("time_allocation"),
                emergency_contact=validated_data.get("emergency_contact")
            )

            # Create associated shifts
            self._create_shifts(member, shifts)

            return member

        except User.DoesNotExist as e:
            raise serializers.ValidationError(f"User does not exist: {e!s}")
        except Department.DoesNotExist as e:
            raise serializers.ValidationError(f"Department does not exist: {e!s}")
        except ValueError as e:
            raise serializers.ValidationError(f"Value error: {e!s}")
        except TypeError as e:
            raise serializers.ValidationError(f"Type error: {e!s}")
        except Exception as e:  # noqa: BLE001
            raise serializers.ValidationError(f"Unexpected error: {e!s}")

    def _create_shifts(self, member, shifts):
        for shift in shifts:
            # Ensure dates are properly parsed
            start_date = parse_date(shift.get("start_date", member.start_date))
            end_date = parse_date(shift.get("end_date", member.end_date)) if shift.get("end_date") else None

            DepartmentMemberShift.objects.create(
                department_member=member,
                shift_template_id=shift["shift_template"],
                assignment_start=start_date,
                assignment_end=end_date
            )

    def _validate_max_hourly(self, shifts, member):
        if shifts:
            generator = ShiftGenerator()

            try:
                # Create a temporary complete member object
                temp_member = SimpleNamespace(
                    user=member.user,
                    department=member.department,
                    start_date=member.start_date,
                    end_date=member.end_date,
                    max_weekly_hours=getattr(member, "max_weekly_hours", 40)  # Default to 40 if not set
                )

                # Calculate projected hours from raw shift data
                projected_hours = generator.calculate_projected_hours_for_data(
                    member=temp_member,
                    shift_data=shifts
                )

                # Convert projected_hours to float/int if it isn't already
                projected_hours = float(projected_hours) if projected_hours else 0
                max_hours = float(temp_member.max_weekly_hours) if temp_member.max_weekly_hours else 0

                if projected_hours > max_hours:
                    raise serializers.ValidationError(
                        f"Projected {projected_hours}h exceeds weekly limit of {max_hours}h"
                    )
            except ShiftTemplate.DoesNotExist as e:
                raise serializers.ValidationError(f"Invalid shift template: {e!s}")
            except AttributeError as e:
                # Add better error handling
                raise serializers.ValidationError(f"Invalid member data: {e!s}")

