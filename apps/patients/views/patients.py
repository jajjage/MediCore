
import logging

from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404
from django_tenants.utils import get_tenant_model, schema_context
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.views import APIView

from apps.patients.base_view.base_patients_view import (
    BasePatientViewSet,
    BaseResponseMixin,
)
from apps.patients.models import (
    Patient,
    PatientDemographics,
)
from apps.patients.models.medical import PatientAllergies
from apps.patients.models.visits import PatientVisit
from apps.patients.serializers import (
    CompletePatientSerializer,
    PatientAllergySerializer,
    PatientChronicConditionSerializer,
    PatientDemographicsSerializer,
    PatientEmergencyContactSerializer,
    PatientSearchSerializer,
    UserSerializer,
)
from hospital.models import HospitalProfile
from hospital.models.hospital_role import Role

logger = logging.getLogger(__name__)
class PatientViewSet(BasePatientViewSet):
    """ViewSet for Patient model with role-based permissions."""

    serializer_class = CompletePatientSerializer
    print(PatientVisit._meta.get_field("patient").remote_field.related_name)
        # For models inheriting BaseModel
    print(PatientAllergies._meta.get_field("patient").remote_field.related_name)  # "allergies"

    def get_queryset(self):
       return Patient.objects.select_related(
            "user"
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

    @action(detail=True, methods=["post", "get"], url_path="update-emergency-contact")
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



class UserCreateView(APIView, BaseResponseMixin):
    basename = "my-user"

    def post(self, request):
        # Get the current tenant's hospital from the public schema
        with schema_context("public"):
            tenant = get_tenant_model().objects.get(schema_name=request.tenant.schema_name)
            hospital = HospitalProfile.objects.get(tenant_id=tenant.id)  # Assuming Hospital is linked to Tenant
            role = Role.objects.get(name=request.data["role"])  # Assuming role_code is passed in request data

        # Pass hospital to serializer context
        serializer = UserSerializer(data=request.data, context={"hospital": hospital, "tenant": tenant, "role": role})
        if serializer.is_valid():
        # Save the user and get the instance
            user = serializer.save()

            # Initialize response data with serializer data
            response_data = serializer.data

        # Only add patient ID if role is Patient
            if role.name.lower() == "patient":
                try:
                    # Access the patient through the reverse relation
                    # Assumes Patient model has OneToOneField to User
                    response_data["patient_id"] = user.patient_profile.id
                except AttributeError:
                    # Handle case where patient profile wasn't created
                    logger.exception(f"Patient profile missing for user {user.id}")
                    response_data["warning"] = "Patient profile not initialized"

            return self.success_response(data=response_data, status_code=201)
        return self.error_response(message=serializer.errors, status_code=400)

