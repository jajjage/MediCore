# from django.shortcuts import get_object_or_404
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from .models import Patient, PatientAddress, PatientDemographics
from .permissions import ROLE_PERMISSIONS, RolePermission
from .serializers import (
    PatientAddressSerializer,
    PatientDemographicsSerializer,
    PatientListCreateSerializer,
)


class PatientViewSet(ModelViewSet):
    """
    ViewSet for Patient model with role-based permissions.
    """
    serializer_class = PatientListCreateSerializer
    permission_classes = [RolePermission]

    def get_queryset(self):
        return Patient.objects.select_related('demographics').prefetch_related('addresses')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    @action(detail=True, methods=['patch'])
    def update_demographics(self, request, pk=None):
        patient = self.get_object()
        user_role = request.user.role
        permissions = ROLE_PERMISSIONS.get(user_role, {})

        if 'add' not in permissions.get('patientdemographics', []):
            return Response(
                {"error": "You don't have permission to update demographics"},
                status=403
            )

        serializer = PatientDemographicsSerializer(
            patient.demographics,
            data=request.data,
            partial=True,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class PatientDemographicsViewSet(ModelViewSet):
    """
    ViewSet for PatientDemographics model with role-based permissions.
    """

    serializer_class = PatientDemographicsSerializer
    permission_classes = [RolePermission]
    
    def get_queryset(self):
        pk = self.kwargs.get("patient_pk")
        print(pk)
        return PatientDemographics.objects.filter(patient_id=self.kwargs.get("patient_pk"))

    def perform_create(self, serializer):
        serializer.save(patient_id=self.kwargs.get("patient_pk"))


class PatientAddressViewSet(ModelViewSet):
    """
    ViewSet for PatientAddress model with role-based permissions.
    """

    serializer_class = PatientAddressSerializer
    permission_classes = [RolePermission]

    def get_queryset(self):
        return PatientAddress.objects.filter(patient_id=self.kwargs.get("patient_pk"))

    def perform_create(self, serializer):
        serializer.save(patient_id=self.kwargs.get("patient_pk"))
