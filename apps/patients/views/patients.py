
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import action

from apps.patients.base_view.base_patients_view import BasePatientViewSet
from apps.patients.models import (
    Patient,
    PatientAddress,
    PatientDemographics,
)
from apps.patients.serializers import (
    CompletePatientSerializer,
    PatientAddressSerializer,
    PatientAllergySerializer,
    PatientChronicConditionSerializer,
    PatientDemographicsSerializer,
    PatientEmergencyContactSerializer,
    PatientSearchSerializer,
)


class PatientViewSet(BasePatientViewSet):
    """ViewSet for Patient model with role-based permissions."""

    serializer_class = CompletePatientSerializer

    def get_queryset(self):
        return Patient.objects.select_related(
            "demographics", "emergency_contact"
        ).prefetch_related(
            "addresses", "allergies", "chronic_conditions", "medical_reports"
        )


    @action(detail=True, methods=["patch"], url_path="update-demographics")
    def update_demographics(self, request, pk=None):
        """Update patient demographics with permission check."""
        patient = self.get_object()

        if not patient.demographics:
            return self.error_response(
                message="Demographics not found for this patient",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        serializer = PatientDemographicsSerializer(
            patient.demographics, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return self.success_response(data=serializer.data, message="Demographics updated successfully")

    @action(detail=True, methods=["post"], url_path="add-allergy")
    def add_allergy(self, request, pk=None):
        """Add allergy to patient with permission check."""
        patient = self.get_object()

        serializer = PatientAllergySerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save(patient=patient)
        return self.success_response(data=serializer.data, message="Allergy added successfully")

    @action(detail=True, methods=["post"], url_path="add-chronic-condition")
    def add_chronic_condition(self, request, pk=None):
        """Add chronic condition to patient with permission check."""
        patient = self.get_object()

        serializer = PatientChronicConditionSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save(patient=patient)
        return self.success_response(data=serializer.data, message="Chronic condition added successfully")

    @action(detail=True, methods=["post"], url_path="update-emergency-contact")
    def update_emergency_contact(self, request, pk=None):
        """Update or create emergency contact with permission check."""
        patient = self.get_object()

        serializer = PatientEmergencyContactSerializer(
            patient.emergency_contact, data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(patient=patient)
        return self.success_response(data=serializer.data, message="Emergency contact updated successfully")

    @action(detail=False, methods=["get"], url_path="search")
    def search(self, request):
        """Search patients based on query parameters."""
        query = request.query_params.get("q", "").strip()
        if not query:
            return self.success_response(data=[], message="No query provided")

        queryset = self.get_queryset().filter(
            Q(pin__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(email__icontains=query)
            | Q(phone_primary__icontains=query)
        )
        serializer = PatientSearchSerializer(queryset, many=True)
        return self.success_response(data=serializer.data, message="Search results retrieved successfully")


class PatientDemographicsViewSet(BasePatientViewSet):
    """ViewSet for PatientDemographics model with role-based permissions."""

    serializer_class = PatientDemographicsSerializer


    def get_queryset(self):
        patient_pk = self.kwargs.get("patient__pk")
        if not patient_pk:
            raise ValueError("patient_pk is required")
        if not Patient.objects.filter(pk=patient_pk).exists():
            raise Http404("Patient not found")
        return PatientDemographics.objects.filter(patient_id=patient_pk)

    def perform_create(self, serializer):
        patient = get_object_or_404(Patient, pk=self.kwargs.get("patient__pk"))
        serializer.save(patient=patient)


class PatientAddressViewSet(BasePatientViewSet):
    """ViewSet for PatientAddress model with role-based permissions."""

    serializer_class = PatientAddressSerializer


    def get_queryset(self):
        return PatientAddress.objects.filter(patient_id=self.kwargs.get("patient__pk"))

    def perform_create(self, serializer):
        serializer.save(patient_id=self.kwargs.get("patient__pk"))


