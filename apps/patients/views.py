from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from .models import (
    Patient,
    PatientAddress,
    PatientAllergy,
    PatientAppointment,
    PatientChronicCondition,
    PatientDemographics,
    PatientDiagnosis,
    PatientMedicalReport,
    PatientOperation,
    PatientPrescription,
    PatientVisit,
)
from .permissions import ROLE_PERMISSIONS, RolePermission
from .serializers import (
    CompletePatientSerializer,
    PatientAddressSerializer,
    PatientAllergySerializer,
    PatientAppointmentSerializer,
    PatientChronicConditionSerializer,
    PatientDemographicsSerializer,
    PatientDiagnosisSerializer,
    PatientEmergencyContactSerializer,
    PatientMedicalReportSerializer,
    PatientOperationSerializer,
    PatientSearchSerializer,
    PatientVisitSerializer,
    PrescriptionSerializer,
)


class PatientViewSet(ModelViewSet):
    """ViewSet for Patient model with role-based permissions."""

    serializer_class = CompletePatientSerializer
    permission_classes = [RolePermission]

    def get_queryset(self):
        return Patient.objects.select_related(
            "demographics", "emergency_contact"
        ).prefetch_related(
            "addresses", "allergies", "chronic_conditions", "medical_reports"
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    def get_object(self):
        """Override get_object to use get_object_or_404."""
        queryset = self.get_queryset()
        obj = get_object_or_404(queryset, id=self.kwargs["pk"])
        self.check_object_permissions(self.request, obj)
        return obj

    @action(detail=True, methods=["patch"])
    def update_demographics(self, request, pk=None):
        """Update patient demographics with permission check."""
        try:
            patient = self.get_object()
            user_role = request.user.role
            permissions = ROLE_PERMISSIONS.get(user_role, {})

            if "change" not in permissions.get("patientdemographics", []):
                return Response(
                    {"error": "You don't have permission to update demographics"},
                    status=status.HTTP_403_FORBIDDEN,
                )

            if not patient.demographics:
                return Response(
                    {"error": "Demographics not found for this patient"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            serializer = PatientDemographicsSerializer(
                patient.demographics,
                data=request.data,
                partial=True,
                context={"request": request},
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)
        except Patient.DoesNotExist:
            return Response(
                {"error": "Patient not found"}, status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=["post"])
    def add_allergy(self, request, pk=None):
        """Add allergy to patient with permission check."""
        patient = self.get_object()
        user_role = request.user.role
        permissions = ROLE_PERMISSIONS.get(user_role, {})

        if "add" not in permissions.get("patientallergy", []):
            return Response(
                {"error": "You don't have permission to add allergies"},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = PatientAllergySerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(patient=patient)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def add_chronic_condition(self, request, pk=None):
        """Add chronic condition to patient with permission check."""
        patient = self.get_object()
        user_role = request.user.role
        permissions = ROLE_PERMISSIONS.get(user_role, {})

        if "add" not in permissions.get("patientchroniccondition", []):
            return Response(
                {"error": "You don't have permission to add chronic conditions"},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = PatientChronicConditionSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(patient=patient)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def update_emergency_contact(self, request, pk=None):
        """Update or create emergency contact with permission check."""
        patient = self.get_object()
        user_role = request.user.role
        permissions = ROLE_PERMISSIONS.get(user_role, {})

        if "change" not in permissions.get("patientemergencycontact", []):
            return Response(
                {"error": "You don't have permission to update emergency contact"},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = PatientEmergencyContactSerializer(
            patient.emergency_contact, data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(patient=patient)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="search")
    def search(self, request):
        query = request.query_params.get("q", "").strip()
        if not query:
            return Response([])

        queryset = self.get_queryset().filter(
            Q(pin__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(email__icontains=query)
            | Q(phone_primary__icontains=query)
        )
        serializer = PatientSearchSerializer(queryset, many=True)
        return Response(serializer.data)


class PatientDemographicsViewSet(ModelViewSet):
    """ViewSet for PatientDemographics model with role-based permissions."""

    serializer_class = PatientDemographicsSerializer
    permission_classes = [RolePermission]

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


class PatientAddressViewSet(ModelViewSet):
    """ViewSet for PatientAddress model with role-based permissions."""

    serializer_class = PatientAddressSerializer
    permission_classes = [RolePermission]

    def get_queryset(self):
        return PatientAddress.objects.filter(patient_id=self.kwargs.get("patient__pk"))

    def perform_create(self, serializer):
        serializer.save(patient_id=self.kwargs.get("patient__pk"))


class PatientAllergyViewSet(ModelViewSet):
    """ViewSet for PatientAllergy model with role-based permissions."""

    serializer_class = PatientAllergySerializer
    permission_classes = [RolePermission]

    def get_queryset(self):
        return PatientAllergy.objects.filter(patient_id=self.kwargs.get("patient__pk"))

    def perform_create(self, serializer):
        serializer.save(patient_id=self.kwargs.get("patient__pk"))


class PatientChronicConditionViewSet(ModelViewSet):
    """ViewSet for PatientChronicCondition model with role-based permissions."""

    serializer_class = PatientChronicConditionSerializer
    permission_classes = [RolePermission]

    def get_queryset(self):
        return PatientChronicCondition.objects.filter(
            patient_id=self.kwargs.get("patient__pk")
        )

    def perform_create(self, serializer):
        serializer.save(patient_id=self.kwargs.get("patient__pk"))


class PatientMedicalReportViewSet(ModelViewSet):
    serializer_class = PatientMedicalReportSerializer
    permission_classes = [RolePermission]
    basename = "patientmedicalreport"

    def get_queryset(self):
        patient_id = self.kwargs.get("patient__pk")
        # Remove the report_id check from here
        return PatientMedicalReport.objects.filter(patient_id=patient_id)

    def get_object(self):
        # Handle single object retrieval here instead
        queryset = self.get_queryset()
        report_id = self.kwargs.get("pk")

        try:
            return queryset.get(id=report_id)
        except PatientMedicalReport.DoesNotExist as err:
            raise NotFound("Report not found for the given patient.") from err

    def perform_create(self, serializer):
        serializer.save(patient_id=self.kwargs.get("patient__pk"))

class PatientVisitViewSet(ModelViewSet):
    """
    ViewSet for managing patient visits.
    """

    permission_classes = [RolePermission]
    serializer_class = PatientVisitSerializer
    basename = "patientcisit"

    def get_queryset(self):
        return PatientVisit.objects.filter(patient_id=self.kwargs.get("patient__pk"))

    def perform_create(self, serializer):
        """
        Save the patient visit record.
        """
        serializer.save(patient_id=self.kwargs.get("patient__pk"))

class PatientOperationViewSet(ModelViewSet):
    """
    ViewSet for managing patient operations.
    """

    permission_classes = [RolePermission]
    serializer_class = PatientOperationSerializer

    def get_queryset(self):
        return PatientOperation.objects.filter(patient_id=self.kwargs.get("patient__pk"))

    def perform_create(self, serializer):
        """
        Save the patient operation record.
        """
        serializer.save(patient_id=self.kwargs.get("patient__pk"))

class PatientDiagnosisViewSet(ModelViewSet):
    """
    ViewSet for managing patient diagnoses.
    """

    permission_classes = [RolePermission]
    serializer_class = PatientDiagnosisSerializer

    def get_queryset(self):
        return PatientDiagnosis.objects.filter(patient_id=self.kwargs.get("patient__pk"))

    def perform_create(self, serializer):
        """
        Save the patient diagnosis record.
        """
        serializer.save(patient_id=self.kwargs.get("patient__pk"))

class PatientAppointmentViewSet(ModelViewSet):
    """
    ViewSet for managing patient appointments.
    """

    permission_classes = [RolePermission]
    serializer_class = PatientAppointmentSerializer

    def get_queryset(self):
        return PatientAppointment.objects.filter(patient_id=self.kwargs.get("patient__pk"))

    def perform_create(self, serializer):
        """
        Save the patient appointment record.
        """
        serializer.save(patient_id=self.kwargs.get("patient__pk"))

class PrescriptionViewSet(ModelViewSet):
    """
    A viewset for managing Prescription instances with optimized querying.

    Supports both patient-specific and individual prescription retrieval.
    """

    serializer_class = PrescriptionSerializer
    permission_classes = [RolePermission]

    def get_queryset(self):
        patient_id = self.kwargs.get("patient_pk")
        if patient_id:
            return PatientPrescription.objects.select_related(
                "appointment__patient",
                "issued_by"
            ).filter(appointment__patient_id=patient_id)

        return PatientPrescription.objects.select_related(
            "appointment__patient",
            "issued_by"
        )

    def get_latest_appointment(self, patient_id):
        """
        Get the latest appointment for the patient that doesn't have a prescription.
        """
        return PatientAppointment.objects.filter(
            patient_id=patient_id,
            prescription__isnull=True
        ).order_by("-appointment_date").first()

    def perform_create(self, serializer):
        """
        Hanf Creates a prescription for a specific patient's appointment.
        """
        patient_id = self.kwargs.get("patient__pk")
        if not patient_id:
            raise ValidationError("Patient ID is required for creating a prescription")

        # Get the latest appointment without a prescription
        appointment = self.get_latest_appointment(patient_id)
        if not appointment:
            raise ValidationError("No available appointments found for prescription creation")

        # Get the staff member instance
        try:
            staff_member = self.request.user
            if not staff_member:
                raise ValidationError("Current user is not associated with a staff member")
        except AttributeError as err:
            raise ValidationError("Current user is not associated with a staff member") from err

        # Save with both appointment and issued_by
        serializer.save(
            appointment=appointment,
            issued_by=staff_member
        )

