# views.py
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.scheduling.utils.filters import ShiftTemplateFilter
from apps.scheduling.utils.shift_generator import ShiftGenerator
from base_view.base_view import BaseViewSet

from .models import ShiftSwapRequest, ShiftTemplate
from .serializers import (
    ShiftGenerationSerializer,
    ShiftSwapRequestSerializer,
    ShiftTemplateSerializer,
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
