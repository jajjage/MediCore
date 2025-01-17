from django.contrib.auth.models import Permission
from django.db import transaction
from rest_framework import serializers

from hospital.models import HospitalProfile

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

    class Meta:
        model = DepartmentMember
        fields = ["id", "department", "user", "role", "start_date", "end_date",
                 "is_primary", "assignment_type", "time_allocation", "emergency_contact",
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


class StaffMemberSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    # role_permissions = serializers.SerializerMethodField()
    current_roles = serializers.SerializerMethodField()
    role = serializers.CharField()
    password = serializers.CharField(write_only=True, required=False)  # For accepting plain password
    hashed_password = serializers.CharField(source="password", read_only=True)  # For displaying hashed password
    primary_department = serializers.SerializerMethodField()
    department_memberships = DepartmentMemberSerializer(many=True, read_only=True)
    doctor_profile = DoctorProfileSerializer(required=False)

    class Meta:
        model = StaffMember
        fields = [
            "id", "email", "first_name", "last_name", "password",
            "full_name", "role", "is_active",
            "current_roles", "primary_department",
            "department_memberships", "doctor_profile", "hashed_password",
        ]
        read_only_fields = [
            "id", "role_permissions", "departments",
            "current_roles", "primary_department", "doctor_profile", "hashed_password",
        ]
        extra_kwargs = {
            "password": {"write_only": True}
        }

    def validate_role(self, value):
        """
        Convert the role name (string) to the corresponding StaffRole object.
        """
        try:
            role = StaffRole.objects.get(name=value)
            return role
        except StaffRole.DoesNotExist as e:
            raise serializers.ValidationError(f"Role '{value}' does not exist.") from e

    def validate(self, data):
        request = self.context.get("request")
        if not request:
            raise serializers.ValidationError("Request object is required in the context.")

        user = request.user

        # Validate required fields
        if request.method == "POST":
            if not data.get("email"):
                raise serializers.ValidationError("Email is required.")
            if not data.get("first_name") or not data.get("last_name"):
                raise serializers.ValidationError("Both first name and last name are required.")


        # Get the hospital profile based on the user's tenant (Client)
        try:
            hospital_profile = HospitalProfile.objects.get(tenant=user.hospital)
            data["hospital"] = hospital_profile
        except HospitalProfile.DoesNotExist as e:
            raise serializers.ValidationError(
                "No hospital profile found for the current user's tenant."
            ) from e
        except Exception as e:
            raise serializers.ValidationError(f"Error getting hospital profile: {e!s}") from e

        return data

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"

    # def get_role_permissions(self, obj):
    #     return [
    #         {
    #             "codename": perm.codename,
    #             "name": perm.name
    #         } for perm in obj.get_role_permissions()
    #     ]

    def get_current_roles(self, obj):
        return list(obj.get_current_roles())

    def get_primary_department(self, obj):
        primary = obj.primary_department
        if primary:
            return DepartmentSerializer(primary.department).data
        return None

    @transaction.atomic
    def create(self, validated_data):
        try:
            doctor_profile_data = validated_data.pop("doctor_profile", {})
            password = validated_data.pop("password", None)

            # Ensure hospital is included in creation
            hospital = validated_data.get("hospital")
            if not hospital:
                request = self.context.get("request")
                if request and hasattr(request.user, "hospital"):
                    try:
                        hospital = HospitalProfile.objects.get(tenant=request.user.hospital)
                        validated_data["hospital"] = hospital
                    except HospitalProfile.DoesNotExist as e:
                        raise (f"Failed to get hospital profile in create method; {(e)}") from e

            # Create the staff member with explicit hospital assignment
            staff_member = StaffMember.objects.create(
                hospital=validated_data.pop("hospital"),
                **validated_data
            )

            if password:
                staff_member.set_password(password)
                staff_member.save()

            # Create doctor profile if data is provided
            if doctor_profile_data:
                DoctorProfile.objects.create(
                    staff_member=staff_member,
                    **doctor_profile_data
                )
            return staff_member
        except Exception as e:
           raise (f"Error creating staff member: {e!s}") from e

    @transaction.atomic
    def update(self, instance, validated_data):
        doctor_profile_data = validated_data.pop("doctor_profile", {})

        if "password" in validated_data:
            password = validated_data.pop("password")
            instance.set_password(password)
            # Save immediately to ensure password is hashed
            instance.save(update_fields=["password"])
        # Update the staff member fields

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update doctor profile if it exists and data is provided
        if doctor_profile_data and hasattr(instance, "doctor_profile"):
            doctor_profile = instance.doctor_profile
            for attr, value in doctor_profile_data.items():
                setattr(doctor_profile, attr, value)
            doctor_profile.save()

        return instance

    def to_representation(self, instance):
        """
        Override to_representation to ensure hospital is included in response.
        """
        data = super().to_representation(instance)
        if instance.hospital:
            data["hospital"] = instance.hospital.id

        # Rename hashed_password to password in the output
        if "hashed_password" in data:
            data["password"] = data.pop("hashed_password")

        return data
