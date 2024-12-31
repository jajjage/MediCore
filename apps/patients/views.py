from rest_framework import  viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from .models import Patient, PatientDemographics, PatientAddress
from .serializers import (
    PatientSerializer, 
    PatientListSerializer,
    PatientDemographicsSerializer,
    PatientAddressSerializer
)
from .permissions import (
    DoctorPermission, 
    NursePermission, 
    ReceptionistPermission, 
    require_staff_role
)

class PatientViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Patient model with role-based permissions
    """
    queryset = Patient.objects.all()
    
    def get_permissions(self):
        """
        Different permissions for different actions
        """
        if self.action in ['create', 'update', 'partial_update']:
            permission_classes = [DoctorPermission|ReceptionistPermission]
        elif self.action == 'destroy':
            permission_classes = [DoctorPermission]
        else:
            permission_classes = [DoctorPermission|NursePermission|ReceptionistPermission]
        return [permission() for permission in permission_classes]

    def get_serializer_class(self):
        if self.action == 'list':
            return PatientListSerializer
        return PatientSerializer

    @action(detail=True, methods=['get'])
    @require_staff_role(['DOCTOR', 'HEAD_DOCTOR', 'NURSE'])
    def demographics(self, request, pk=None):
        patient = self.get_object()
        demographics = get_object_or_404(PatientDemographics, patient=patient)
        serializer = PatientDemographicsSerializer(demographics)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    @require_staff_role(['DOCTOR', 'HEAD_DOCTOR', 'NURSE'])
    def addresses(self, request, pk=None):
        patient = self.get_object()
        addresses = PatientAddress.objects.filter(patient=patient)
        serializer = PatientAddressSerializer(addresses, many=True)
        return Response(serializer.data)

class PatientDemographicsViewSet(viewsets.ModelViewSet):
    serializer_class = PatientDemographicsSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [DoctorPermission|NursePermission]
        else:
            permission_classes = [DoctorPermission|NursePermission|ReceptionistPermission]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        return PatientDemographics.objects.filter(
            patient_id=self.kwargs.get('patient_pk')
        )

class PatientAddressViewSet(viewsets.ModelViewSet):
    serializer_class = PatientAddressSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [ReceptionistPermission]
        else:
            permission_classes = [DoctorPermission|NursePermission|ReceptionistPermission]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        return PatientAddress.objects.filter(
            patient_id=self.kwargs.get('patient_pk')
        )