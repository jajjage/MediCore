from django.db import transaction
from django.db.models import Sum
from django.utils.timezone import now
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from .base.staff_base_viewset import BaseViewSet
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
from .serializers import (
    DepartmentMemberSerializer,
    DepartmentSerializer,
    DoctorProfileSerializer,
    NurseProfileSerializer,
    StaffMemberSerializer,
    StaffRoleSerializer,
    StaffTransferSerializer,
    TechnicianProfileSerializer,
    WorkloadAssignmentSerializer,
)
from .utils.exceptions import BusinessLogicError
from .utils.filters import (
    DepartmentFilter,
    DoctorProfileFilter,
    NurseProfileFilter,
    StaffMemberFilter,
    StaffTransferFilter,
    TechnicianProfileFilter,
    WorkloadAssignmentFilter,
)
from .utils.response_handlers import APIResponse


class DepartmentViewSet(BaseViewSet):
    serializer_class = DepartmentSerializer
    filterset_class = DepartmentFilter
    search_fields = ["name", "code", "description"]
    ordering_fields = ["name", "created_at", "department_type"]

    queryset = Department.objects.select_related(
        "parent_department",
        "hospital",
        "department_head"
    ).prefetch_related(
        "sub_departments",
        "staff_members"
    )

    @extend_schema(
        parameters=[
            OpenApiParameter(name="active_only", type=bool, description="Filter only active staff")
        ]
    )
    @action(detail=True, methods=["get"])
    def staff_list(self, request, pk=None):
        """Get list of staff members in department."""
        try:
            department = self.get_object()
            active_only = request.query_params.get("active_only", "true").lower() == "true"

            staff = department.staff_members.filter(is_active=active_only)
            serializer = StaffMemberSerializer(staff, many=True, context={"request": request})

            return APIResponse.success(
                data=serializer.data,
                message="Successfully retrieved department staff list",
                extra={
                    "total_count": staff.count(),
                    "department_name": department.name,
                    "active_only": active_only
                }
            )
        except Exception as e:
            return self.handle_exception(e)

    @transaction.atomic
    def perform_create(self, serializer):
        try:
            hospital = self.get_hospital_from_user()
            if not hospital:
                raise BusinessLogicError(
                    message="No hospital associated with current user",
                    error_code="NO_HOSPITAL_ACCESS"
                )

            instance = serializer.save(hospital=hospital)

            if instance.department_head:
                DepartmentMember.objects.create(
                    department=instance,
                    user=instance.department_head,
                    role="HEAD",
                    start_date=now(),
                    is_primary=True
                )
            return APIResponse.success(
                data=self.get_serializer(instance).data,
                message="Department created successfully",
                status_code=status.HTTP_201_CREATED
            )
        except Exception as e:
            return self.handle_exception(e)

class StaffMemberViewSet(BaseViewSet):
    serializer_class = StaffMemberSerializer
    filterset_class = StaffMemberFilter
    search_fields = ["first_name", "last_name", "email"]
    ordering_fields = ["first_name", "last_name", "created_at"]

    queryset = StaffMember.objects.select_related(
        "hospital",
        "role"
    ).prefetch_related(
        "department_memberships__department",
        "role__permissions"
    )

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def assign_to_department(self, request, pk=None):
        """Assign staff member to a department."""
        try:
            staff_member = self.get_object()
            serializer = DepartmentMemberSerializer(data=request.data)

            if not serializer.is_valid():
                return APIResponse.validation_error(serializer.errors)

            instance = serializer.save(user=staff_member)
            return APIResponse.success(
                data=serializer.data,
                message="Staff member successfully assigned to department",
                status_code=status.HTTP_201_CREATED,
                extra={
                    "department_name": instance.department.name,
                    "staff_name": staff_member.get_full_name()
                }
            )
        except Exception as e:
            return self.handle_exception(e)

    @action(detail=True, methods=["get"])
    def schedule(self, request, pk=None):
        """Get staff member's schedule."""
        try:
            staff_member = self.get_object()
            profile = staff_member.staff_profile

            if not profile:
                return APIResponse.not_found(
                    message="Staff profile not found",
                    resource_type="Staff Profile"
                )

            schedule_data = getattr(profile, "availability", None) or getattr(profile, "shift_preferences", {})
            return APIResponse.success(
                data=schedule_data,
                message="Successfully retrieved staff schedule",
                extra={"staff_name": staff_member.get_full_name()}
            )
        except Exception as e:
            return self.handle_exception(e)

class StaffRoleViewSet(BaseViewSet):
    serializer_class = StaffRoleSerializer
    queryset = StaffRole.objects.prefetch_related("permissions")

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def assign_permissions(self, request, pk=None):
        """Assign permissions to role."""
        try:
            role = self.get_object()
            permissions = request.data.get("permissions", [])

            if not permissions:
                raise BusinessLogicError(
                    message="No permissions provided",
                    error_code="NO_PERMISSIONS"
                )

            role.permissions.set(permissions)
            return APIResponse.success(
                data=self.get_serializer(role).data,
                message="Permissions successfully assigned to role"
            )
        except Exception as e:
            return self.handle_exception(e)
class BaseProfileViewSet(BaseViewSet):
    ordering_fields = ["years_of_experience", "qualification"]

    @action(detail=True, methods=["get"])
    def availability(self, request, pk=None):
        profile = self.get_object()
        availability_data = getattr(profile, "availability", None) or getattr(profile, "shift_preferences", {})
        return Response(availability_data)

class DoctorProfileViewSet(BaseProfileViewSet):
    serializer_class = DoctorProfileSerializer
    filterset_class = DoctorProfileFilter
    search_fields = ["specialization", "license_number"]
    queryset = DoctorProfile.objects.select_related("staff_member")

    @action(detail=True, methods=["get"])
    def patient_load(self, request, pk=None):
        try:
            doctor = self.get_object()
            current_patients = doctor.current_patient_count
            max_patients = doctor.max_patients_per_day
            available_slots = max_patients - current_patients

            return APIResponse.success(
                data={
                    "current_patients": current_patients,
                    "max_patients": max_patients,
                    "available_slots": available_slots
                },
                message="Successfully retrieved patient load",
                extra={
                    "doctor_name": doctor.staff_member.get_full_name(),
                    "capacity_percentage": (current_patients / max_patients) * 100
                }
            )
        except Exception as e:
            return self.handle_exception(e)

class NurseProfileViewSet(BaseProfileViewSet):
    serializer_class = NurseProfileSerializer
    filterset_class = NurseProfileFilter
    search_fields = ["ward_specialty", "nurse_license"]

    def get_queryset(self):
        queryset = NurseProfile.objects.select_related("staff_member")
        return super().get_queryset().filter(queryset)

    @action(detail=True, methods=["get"])
    def ward_assignments(self, request, pk=None):
        nurse = self.get_object()
        return Response(nurse.shift_preferences)

class TechnicianProfileViewSet(BaseProfileViewSet):
    serializer_class = TechnicianProfileSerializer
    filterset_class = TechnicianProfileFilter
    search_fields = ["equipment_specialties", "technician_license"]

    def get_queryset(self):
        queryset = TechnicianProfile.objects.select_related("staff_member")
        return super().get_queryset().filter(queryset)

    @action(detail=True, methods=["get"])
    def certifications(self, request, pk=None):
        technician = self.get_object()
        return Response({
            "equipment_specialties": technician.equipment_specialties,
            "lab_certifications": technician.lab_certifications
        })


class DepartmentMemberViewSet(BaseViewSet):
    serializer_class = DepartmentMemberSerializer
    queryset = DepartmentMember.objects.select_related("department", "user")

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def end_assignment(self, request, pk=None):
        """End a department assignment with proper checks and workflows."""
        try:
            assignment = self.get_object()
            end_date = request.data.get("end_date")

            if not end_date:
                raise BusinessLogicError(
                    message="End date is required",
                    error_code="END_DATE_REQUIRED"
                )

            department = assignment.department
            future_staff_count = department.get_active_staff().filter(
                end_date__gt=end_date
            ).count()

            if future_staff_count < department.minimum_staff_required:
                raise BusinessLogicError(
                    message="Cannot end assignment - minimum staffing levels not maintained",
                    error_code="MIN_STAFF_VIOLATION"
                )

            transfer_to = request.data.get("transfer_to_department")
            if transfer_to:
                transfer = assignment.initiate_transfer(
                    to_department=transfer_to,
                    transfer_type="PERMANENT",
                    effective_date=end_date,
                    reason=request.data.get("reason")
                )
                extra_data = {"transfer_id": transfer.id}
            else:
                assignment.end_date = end_date
                assignment.is_active = False
                assignment.full_clean()
                assignment.save()
                extra_data = {}

            return APIResponse.success(
                data=self.get_serializer(assignment).data,
                message="Assignment ended successfully",
                extra={
                    "staff_name": assignment.user.get_full_name(),
                    "department_name": department.name,
                    **extra_data
                }
            )
        except Exception as e:
            return self.handle_exception(e)

class WorkloadAssignmentViewSet(BaseViewSet):
    serializer_class = WorkloadAssignmentSerializer
    filterset_class = WorkloadAssignmentFilter
    ordering_fields = ["week_start_date", "scheduled_hours"]
    queryset = WorkloadAssignment.objects.select_related(
        "department_member",
        "department_member__department",
        "department_member__user"
    )

    @action(detail=False, methods=["get"])
    def department_summary(self, request):
        """Get workload summary for department."""
        try:
            department_id = request.query_params.get("department")
            if not department_id:
                raise BusinessLogicError(
                    message="Department ID is required",
                    error_code="DEPARTMENT_REQUIRED"
                )

            summary = self.get_queryset().filter(
                department_member__department_id=department_id
            ).aggregate(
                total_scheduled=Sum("scheduled_hours"),
                total_actual=Sum("actual_hours"),
                total_on_call=Sum("on_call_hours")
            )

            return APIResponse.success(
                data=summary,
                message="Successfully retrieved department workload summary",
                extra={"department_id": department_id}
            )
        except Exception as e:
            return self.handle_exception(e)

class StaffTransferViewSet(BaseViewSet):
    serializer_class = StaffTransferSerializer
    filterset_class = StaffTransferFilter
    ordering_fields = ["effective_date", "transfer_type"]
    queryset = StaffTransfer.objects.select_related(
        "from_assignment",
        "to_assignment",
        "approved_by"
    )

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def approve_transfer(self, request, pk=None):
        try:
            transfer = self.get_object()
            if transfer.approved_by:
                raise BusinessLogicError(
                    message="Transfer already approved",
                    error_code="TRANSFER_ALREADY_APPROVED"
                )

            transfer.approved_by = request.user.staff_member
            transfer.save()

            from_assignment = transfer.from_assignment
            from_assignment.end_date = transfer.effective_date
            from_assignment.is_active = False
            from_assignment.save()

            return APIResponse.success(
                data=self.get_serializer(transfer).data,
                message="Transfer successfully approved",
                extra={
                    "staff_name": transfer.from_assignment.user.get_full_name(),
                    "from_department": transfer.from_assignment.department.name,
                    "to_department": transfer.to_assignment.department.name,
                    "effective_date": transfer.effective_date
                }
            )
        except Exception as e:
            return self.handle_exception(e)
