from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from .models import Patient, PatientDemographics, PatientAddress
from .serializers import (
    PatientSerializer,
    PatientListSerializer,
    PatientDemographicsSerializer,
    PatientAddressSerializer,
)
from .permissions import RolePermission


class PatientViewSet(ModelViewSet):
    """
    ViewSet for Patient model with role-based permissions.
    """
    queryset = Patient.objects.all()
    permission_classes = [RolePermission]

    def get_serializer_class(self):
        if self.action == 'list':
            return PatientListSerializer
        return PatientSerializer

    @action(detail=True, methods=['get'], permission_classes=[RolePermission])
    def demographics(self, request, pk=None):
        """
        Retrieve patient demographics.
        """
        patient = self.get_object()
        demographics = get_object_or_404(PatientDemographics, patient=patient)
        serializer = PatientDemographicsSerializer(demographics)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], permission_classes=[RolePermission])
    def addresses(self, request, pk=None):
        """
        Retrieve patient addresses.
        """
        patient = self.get_object()
        addresses = PatientAddress.objects.filter(patient=patient)
        serializer = PatientAddressSerializer(addresses, many=True)
        return Response(serializer.data)


class PatientDemographicsViewSet(ModelViewSet):
    """
    ViewSet for PatientDemographics model with role-based permissions.
    """
    serializer_class = PatientDemographicsSerializer
    permission_classes = [RolePermission]

    def get_queryset(self):
        return PatientDemographics.objects.filter(
            patient_id=self.kwargs.get('patient_pk')
        )

    def perform_create(self, serializer):
        serializer.save(patient_id=self.kwargs.get('patient_pk'))


class PatientAddressViewSet(ModelViewSet):
    """
    ViewSet for PatientAddress model with role-based permissions.
    """
    serializer_class = PatientAddressSerializer
    permission_classes = [RolePermission]

    def get_queryset(self):
        return PatientAddress.objects.filter(
            patient_id=self.kwargs.get('patient_pk')
        )

    def perform_create(self, serializer):
        serializer.save(patient_id=self.kwargs.get('patient_pk'))
