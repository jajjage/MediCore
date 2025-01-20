
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.patients.base_view.base_patients_view import BasePatientViewSet
from apps.patients.models import (
    PatientOperation,
)
from apps.patients.serializers import (
    PatientOperationSerializer,
)
from apps.patients.services.operation_service import OperationService


class PatientOperationViewSet(BasePatientViewSet):
    """
    ViewSet for managing patient operations.
    """

    serializer_class = PatientOperationSerializer

    print("operation view")
    def get_queryset(self):
        return PatientOperation.objects.filter(
            patient_id=self.kwargs.get("patient__pk")
        )

    def perform_create(self, serializer):
        OperationService.create_operation(
            serializer,
            self.request.user,
            self.kwargs.get("patient__pk")
        )

    def perform_update(self, serializer):
        OperationService.update_operation(
            serializer,
            self.request.user
        )

    @action(detail=True, methods=["patch"])
    def reschedule(self, request, patient_pk=None, pk=None):
        """
        Handle special endpoint for rescheduling appointments.
        """
        operation = self.get_object()
        serializer = self.get_serializer(
            operation,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():
            OperationService.update_operation(
                serializer,
                self.request.user
            )
            return Response(serializer.data)
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )
