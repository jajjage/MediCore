# views.py
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.scheduling.utils.filters import ShiftTemplateFilter
from base_view.base_view import BaseViewSet

from .models import ShiftTemplate
from .serializers import ShiftTemplateSerializer


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
