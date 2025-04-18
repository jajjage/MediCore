import logging

from django.db import connection, transaction
from django.db.models import Sum
from django.db.transaction import on_commit
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from base_view import BaseViewSet
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
from .serializers import (
    DepartmentMemberSerializer,
    DepartmentSerializer,
    DoctorProfileSerializer,
    NurseProfileSerializer,
    StaffTransferSerializer,
    TechnicianProfileSerializer,
    WorkloadAssignmentSerializer,
)
from .utils.date_validators import date_validation
from .utils.exceptions import BusinessLogicError
from .utils.filters import (
    DepartmentFilter,
    DoctorProfileFilter,
    NurseProfileFilter,
    StaffTransferFilter,
    TechnicianProfileFilter,
    WorkloadAssignmentFilter,
)
from .utils.response_handlers import APIResponse

logger = logging.getLogger(__name__)
class DepartmentViewSet(BaseViewSet):
    serializer_class = DepartmentSerializer
    filterset_class = DepartmentFilter
    search_fields = ["name", "code", "description"]
    ordering_fields = ["name", "created_at", "department_type"]

    queryset = Department.objects.select_related(
        "parent_department",
        "department_head"
    ).prefetch_related(
        "sub_departments",
        "department_members"
    )

class BaseProfileViewSet(BaseViewSet):
    ordering_fields = ["years_of_experience", "qualification"]

    @action(detail=True, methods=["get"])
    def availability(self, request, pk=None):
        profile = self.get_object()
        availability_data = getattr(profile, "availability", None) or getattr(profile, "shift_preferences", {})
        return Response(availability_data)

class DoctorProfileViewSet(BaseViewSet):
    serializer_class = DoctorProfileSerializer
    filterset_class = DoctorProfileFilter
    search_fields = ["specialization", "license_number"]
    queryset = DoctorProfile.objects.select_related("user")

class NurseProfileViewSet(BaseProfileViewSet):
    serializer_class = NurseProfileSerializer
    filterset_class = NurseProfileFilter
    search_fields = ["ward_specialty", "nurse_license"]
    lookup_field = "id"

    def get_queryset(self):
        return NurseProfile.objects.select_related("user")

    def get_object(self):
        try:
            return get_object_or_404(self.get_queryset(), id=self.kwargs["id"])
        except (ValueError, TypeError):
            return self.error_response(
                message={"error": "Invalid UUID format"},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=["get"])
    def ward_assignments(self, request, id=None):  # noqa: A002
        try:
            nurse = self.get_object()
            return self.success_response(data=nurse.shift_preferences)
        except NurseProfile.DoesNotExist:
            return self.error_response(
                message={"error": "Nurse profile not found"},
                status=status.HTTP_404_NOT_FOUND
            )

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

    def perform_create(self, serializer):
        try:
            with transaction.atomic():
                instance = serializer.save()  # noqa: F841

            headers = self.get_success_headers(serializer.data)
            return self.success_response(
                data=serializer.data,
                status_code=status.HTTP_201_CREATED,
                message=headers
            )
        except Exception as e:
            print(f"Error in perform_create: {e!s}")
            print(f"Error type: {type(e)}")
            raise

    @action(detail=True, methods=["get"])
    def workload_analysis(self, request, pk=None):
        """Get detailed workload analysis for staff member."""
        member = self.get_object()
        workload = DepartmentMember.get_staff_workload(member.user)
        return APIResponse.success(data=workload)


    @action(detail=True, methods=["post"])
    @transaction.atomic
    def end_assignment(self, request, pk=None):
        """End a department assignment."""
        try:
            data = request.data
            assignment = self.get_object()

            end_date = date_validation(data)
            # Check staffing requirements
            requirements = assignment.check_staffing_requirements()
            print(requirements["current_staff_count"])
            if requirements["requires_replacement"] and not data.get("transfer_to_department"):
                raise BusinessLogicError(
                    "Immediate replacement required for this role",
                    "REPLACEMENT_REQUIRED"
                )

            if not requirements["does_minimum_staff_met"]:
                raise BusinessLogicError(
                    f"Cannot end assignment - minimum staffing levels not maintained "
                    f"(Current: {requirements['current_staff_count']}, "
                    f"Required: {requirements['minimum_required']})",
                    "MIN_STAFF_VIOLATION"
                )

            # Handle transfer if specified
            if data.get("transfer_to_department"):
                # Create a separate view action for transfers
                return self.transfer_assignment(request, assignment, end_date)

            # End the assignment
            assignment.end_assignment(end_date, data.get("reason"))

            return APIResponse.success(
                data=self.get_serializer(assignment).data,
                message="Assignment ended successfully",
                extra={
                    "staff_name": assignment.user.get_full_name(),
                    "department_name": assignment.department.name,
                    "staffing_requirements": requirements
                }
            )

        except BusinessLogicError as e:
            return APIResponse.error(message=str(e), error_code=e.error_code)
        except ValidationError as e:
            return APIResponse.error(message=str(e), error_code="VALIDATION_ERROR")
        except Exception as e:
            logger.exception(f"Unexpected error in end_assignment: {e!s}")
            return APIResponse.error(
                message="An unexpected error occurred",
                error_code="INTERNAL_SERVER_ERROR",
                status_code=500
            )

    def transfer_assignment(self, request, assignment, effective_date):
        """Handle transfer of assignment to new department."""
        try:
            transfer = assignment.initiate_transfer(
                to_department=request.data["transfer_to_department"],
                transfer_type=request.data.get("transfer_type", "PERMANENT"),
                effective_date=effective_date,
                reason=request.data.get("reason")
            )

            return APIResponse.success(
                data=self.get_serializer(assignment).data,
                message="Assignment transfer initiated successfully",
                extra={
                    "staff_name": assignment.user.get_full_name(),
                    "department_name": assignment.department.name,
                    "transfer_id": transfer.id
                }
            )
        except BusinessLogicError as e:
            return APIResponse.error(message=str(e), error_code=e.error_code)

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
        except Exception as e:  # noqa: BLE001
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
        except BusinessLogicError as ble:
            return self.handle_exception(ble)
        except Exception as e:
            logger.exception(f"Business logic error in end_assignment: {e!s}")
            return self.handle_exception(e)
