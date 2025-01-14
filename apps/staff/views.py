from time import timezone

from django.core.exceptions import ValidationError
from django.db import connection, transaction
from django.db.models import Sum
from django_filters import rest_framework as django_filters
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core import serializers

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
from .permissions import TenantModelPermission
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
from .utils.filters import (
    DepartmentFilter,
    DoctorProfileFilter,
    NurseProfileFilter,
    StaffMemberFilter,
    StaffTransferFilter,
    TechnicianProfileFilter,
    WorkloadAssignmentFilter,
)


# Base ViewSet with common functionality
class BaseViewSet(viewsets.ModelViewSet):
    permission_classes = [TenantModelPermission]
    filter_backends = [
        django_filters.DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter
    ]
    queryset = None

    def get_queryset(self):
        user = self.request.user
        if not user.has_tenant_access(connection.schema_name):
            return self.queryset.none()
        return self.queryset

# ViewSets
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

    def get_queryset(self):
        queryset = super().get_queryset()
        # Get the HospitalProfile instance from the user
        user = self.request.user
        user_hospital = getattr(user, "administered_hospital", None) or getattr(user, "associated_hospitals", None)
        print(user_hospital)
        if user_hospital:
            return queryset.filter(hospital=user_hospital)
        return queryset.none()

    @extend_schema(
        parameters=[
            OpenApiParameter(name="active_only", type=bool, description="Filter only active staff")
        ]
    )
    @action(detail=True, methods=["get"])
    def staff_list(self, request, pk=None):
        """Get list of staff members in department."""
        department = self.get_object()
        active_only = request.query_params.get("active_only", "true").lower() == "true"

        staff = department.staff_members.filter(is_active=active_only)
        serializer = StaffMemberSerializer(
            staff,
            many=True,
            context={"request": request}
        )
        return Response(serializer.data)

    @transaction.atomic
    def perform_create(self, serializer):
        try:
            instance = serializer.save()
            # Create department head assignment if specified
            if instance.department_head:
                DepartmentMember.objects.create(
                    department=instance,
                    user=instance.department_head,
                    role="HEAD",
                    start_date=timezone.now().date(),
                    is_primary=True
                )
        except ValidationError as e:
            raise serializers.ValidationError(e.message_dict) from e

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

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        user_hospital = getattr(user, "administered_hospital", None) or getattr(user, "associated_hospitals", None)
        print(user_hospital)
        if user_hospital:
            return queryset.filter(hospital=user_hospital)
        return queryset.none()

    @transaction.atomic
    def perform_create(self, serializer):
        instance = serializer.save()
        # Create specialized profile based on role
        role_code = instance.role.code
        if role_code == "DOCTOR":
            DoctorProfile.objects.create(staff_member=instance)
        elif role_code == "NURSE":
            NurseProfile.objects.create(staff_member=instance)
        elif role_code == "TECHNICIAN":
            TechnicianProfile.objects.create(staff_member=instance)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def assign_to_department(self, request, pk=None):
        """Assign staff member to a department."""
        staff_member = self.get_object()
        serializer = DepartmentMemberSerializer(data=request.data)

        if serializer.is_valid():
            try:
                serializer.save(user=staff_member)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            except ValidationError as e:
                return Response(
                    {"detail": str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["get"])
    def schedule(self, request, pk=None):
        """Get staff member's schedule."""
        staff_member = self.get_object()
        profile = staff_member.staff_profile

        if not profile:
            return Response(
                {"detail": "No profile found"},
                status=status.HTTP_404_NOT_FOUND
            )

        schedule_data = {}
        if hasattr(profile, "availability"):
            schedule_data = profile.availability
        elif hasattr(profile, "shift_preferences"):
            schedule_data = profile.shift_preferences

        return Response(schedule_data)

class StaffRoleViewSet(BaseViewSet):
    serializer_class = StaffRoleSerializer
    search_fields = ["name", "code", "description"]
    ordering_fields = ["name", "category"]
    filterset_fields = ["category", "is_active"]

    def get_queryset(self):
        queryset = StaffRole.objects.prefetch_related("permissions")
        return super().get_queryset().filter(queryset)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def assign_permissions(self, request, pk=None):
        """Assign permissions to role."""
        role = self.get_object()
        permissions = request.data.get("permissions", [])

        try:
            role.permissions.set(permissions)
            return Response(
                StaffRoleSerializer(role).data,
                status=status.HTTP_200_OK
            )
        except (ValidationError, StaffRole.permissions.RelatedObjectDoesNotExist) as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

class DepartmentMemberViewSet(BaseViewSet):
    serializer_class = DepartmentMemberSerializer
    search_fields = ["user__first_name", "user__last_name", "role"]
    ordering_fields = ["start_date", "created_at"]
    filterset_fields = ["department", "role", "is_active"]

    def get_queryset(self):
        queryset = DepartmentMember.objects.select_related(
            "department",
            "user"
        )
        return super().get_queryset().filter(queryset)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def end_assignment(self, request, pk=None):
        """End a department assignment with proper checks and workflows."""
        assignment = self.get_object()
        end_date = request.data.get("end_date")
        reason = request.data.get("reason")
        transfer_to = request.data.get("transfer_to_department")

        if not end_date:
            return Response({"detail": "End date is required"},
                        status=status.HTTP_400_BAD_REQUEST)

        try:
            # Validate staffing levels
            department = assignment.department
            future_staff_count = department.get_active_staff().filter(
                end_date__gt=end_date
            ).count()

            if future_staff_count < department.minimum_staff_required:
                raise ValidationError(
                    "Cannot end assignment - minimum staffing levels not maintained"
                )

            # Handle transfer if specified
            if transfer_to:
                transfer = assignment.initiate_transfer(
                    to_department=transfer_to,
                    transfer_type="PERMANENT",
                    effective_date=end_date,
                    reason=reason
                )

            # Regular end assignment
            else:
                assignment.end_date = end_date
                assignment.is_active = False
                assignment.full_clean()
                assignment.save()

            # Trigger notifications
            # notify_department_head.delay(
            #     department.id,
            #     f"Staff assignment ending: {assignment.user.get_full_name()}"
            # )

            return Response(DepartmentMemberSerializer(assignment).data)

        except ValidationError as e:
            return Response({"detail": str(e)},
                        status=status.HTTP_400_BAD_REQUEST)

class WorkloadAssignmentViewSet(BaseViewSet):
    serializer_class = WorkloadAssignmentSerializer
    filterset_class = WorkloadAssignmentFilter
    ordering_fields = ["week_start_date", "scheduled_hours"]

    def get_queryset(self):
        queryset = WorkloadAssignment.objects.select_related(
            "department_member",
            "department_member__department",
            "department_member__user"
        )
        return super().get_queryset().filter(queryset)

    @action(detail=False, methods=["get"])
    def department_summary(self, request):
        """Get workload summary for department."""
        department_id = request.query_params.get("department")
        if not department_id:
            return Response(
                {"detail": "Department ID required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        summary = self.get_queryset().filter(
            department_member__department_id=department_id
        ).aggregate(
            total_scheduled=Sum("scheduled_hours"),
            total_actual=Sum("actual_hours"),
            total_on_call=Sum("on_call_hours")
        )
        return Response(summary)

class StaffTransferViewSet(BaseViewSet):
    serializer_class = StaffTransferSerializer
    filterset_class = StaffTransferFilter
    ordering_fields = ["effective_date", "transfer_type"]

    def get_queryset(self):
        queryset = StaffTransfer.objects.select_related(
            "from_assignment",
            "to_assignment",
            "approved_by"
        )
        return super().get_queryset().filter(queryset)

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def approve_transfer(self, request, pk=None):
        transfer = self.get_object()
        if transfer.approved_by:
            return Response(
                {"detail": "Transfer already approved"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            transfer.approved_by = request.user.staff_member
            transfer.save()

            # Update department assignments
            from_assignment = transfer.from_assignment
            from_assignment.end_date = transfer.effective_date
            from_assignment.is_active = False
            from_assignment.save()

            return Response(self.get_serializer(transfer).data)
        except ValidationError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

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

    def get_queryset(self):
        queryset = DoctorProfile.objects.select_related("staff_member")
        return super().get_queryset().filter(queryset)

    @action(detail=True, methods=["get"])
    def patient_load(self, request, pk=None):
        doctor = self.get_object()
        current_patients = doctor.current_patient_count
        max_patients = doctor.max_patients_per_day
        return Response({
            "current_patients": current_patients,
            "max_patients": max_patients,
            "available_slots": max_patients - current_patients
        })

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
