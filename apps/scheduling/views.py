# views.py
from datetime import timezone

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.scheduling.utils.filters import ShiftTemplateFilter
from apps.scheduling.utils.shift_generator import ShiftGenerator
from base_view.base_view import BaseViewSet

from .models import (
    NurseAvailability,
    ShiftSwapRequest,
    ShiftTemplate,
    UserShiftPreference,
)
from .serializers import (
    NurseAvailabilitySerializer,
    ShiftGenerationSerializer,
    ShiftSwapRequestSerializer,
    ShiftTemplateSerializer,
    UserShiftPreferenceSerializer,
)
from .tasks import process_swap_request_task


class ShiftTemplateViewSet(BaseViewSet):
    queryset = ShiftTemplate.objects.all()
    serializer_class = ShiftTemplateSerializer
    permission_classes = [IsAuthenticated]
    filterset_class = ShiftTemplateFilter
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["department", "type", "recurrence", "role_requirement", "is_active"]
    search_fields = ["name"]
    ordering_fields = ["name", "start_time", "valid_from"]
    ordering = ["name"]

    def get_queryset(self):
        queryset = super().get_queryset()
        # Filter out inactive templates by default unless explicitly requested
        if not self.request.query_params.get("include_inactive"):
            queryset = queryset.filter(is_active=True)
        return queryset

    @action(detail=True, methods=["post"])
    def toggle_active(self, request, pk=None):
        template = self.get_object()
        template.is_active = not template.is_active
        template.save()
        return Response({"is_active": template.is_active})

    @action(detail=False, methods=["get"])
    def by_department(self, request):
        department_id = request.query_params.get("department_id")
        if not department_id:
            return Response({"error": "department_id is required"}, status=400)

        templates = self.get_queryset().filter(department_id=department_id)
        serializer = self.get_serializer(templates, many=True)
        return Response(serializer.data)


class ShiftGenerationViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def create(self, request):
        serializer = ShiftGenerationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {"message": "Initial shifts generation task started"},
            status=status.HTTP_202_ACCEPTED
        )
class ShiftSwapRequestViewSet(BaseViewSet):
    queryset = ShiftSwapRequest.objects.all()
    serializer_class = ShiftSwapRequestSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["status"]
    search_fields = ["original_shift__id", "requesting_user__username", "requested_user__username"]
    ordering_fields = ["created_at", "status"]
    ordering = ["-created_at"]

    def perform_create(self, serializer):
        requesting_user = self.request.user
        serializer.save(requesting_user=requesting_user)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        schema_name = request.tenant.schema_name
        swap_request = self.get_object()
        swap_request.status = ShiftSwapRequest.Status.APPROVED
        swap_request.save()
        try:
            process_swap_request_task.delay(swap_request.id, schema_name)
        except Exception as e:  # noqa: BLE001
            return self.success_response(data=str(e), status=status.HTTP_400_BAD_REQUEST)
        return Response({"status": swap_request.status})

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        swap_request = self.get_object()
        swap_request.status = ShiftSwapRequest.Status.REJECTED
        swap_request.save()
        return self.success_response(data={"status": swap_request.status})



class NurseAvailabilityViewSet(BaseViewSet):
    """
    A viewset that provides the standard actions to create, retrieve, update.

    and delete NurseAvailability records. Nurses can only access and modify
    their own availability entries.
    """

    serializer_class = NurseAvailabilitySerializer

    def get_queryset(self):
        # Each nurse can only see their own availability records
        return NurseAvailability.objects.all()

    def perform_create(self, serializer):
        # Automatically assign the logged-in user to the availability record
        serializer.save()

    @action(detail=False, methods=["get"], url_path="upcoming")
    def upcoming(self, request):
        """
        ACustom action to list all upcoming availability entries (where the start_date.

        is today or in the future) for the logged-in nurse.
        """
        today = timezone.now().date()
        upcoming_records = self.get_queryset().filter(start_date__gte=today)
        serializer = self.get_serializer(upcoming_records, many=True)
        return Response(serializer.data)

class UserShiftPreferenceViewSet(BaseViewSet):
    serializer_class = UserShiftPreferenceSerializer


    def get_queryset(self):
        """
        Filter queryset based on user permissions.

        - Staff/admins can see all records
        - Regular users can only see their own records
        """
        user = self.request.user
        queryset = UserShiftPreference.objects.all().select_related(
            "user", "department"
        ).prefetch_related("preferred_shift_types")

        if not (user.is_staff or user.is_superuser):
            queryset = queryset.filter(user=user)

        # Allow filtering by department
        department_id = self.request.query_params.get("department_id")
        if department_id:
            queryset = queryset.filter(department_id=department_id)

        return queryset

    def perform_create(self, serializer):
        """Ensure the user is set to the current user for new records."""
        serializer.save()

    @action(detail=False, methods=["get"])
    def my_preferences(self, request):
        """Endpoint to get current user's preferences."""
        queryset = self.get_queryset().filter(user=request.user)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["patch"])
    def update_shift_types(self, request, pk=None):
        """Endpoint to update only the preferred shift types."""
        instance = self.get_object()

        shift_type_ids = request.data.get("preferred_shift_type_ids", [])

        if not isinstance(shift_type_ids, list):
            return Response(
                {"error": "preferred_shift_type_ids must be a list"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            shift_types = ShiftTemplate.objects.filter(id__in=shift_type_ids)
            instance.preferred_shift_types.set(shift_types)
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
        except (ValidationError, ObjectDoesNotExist) as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
