from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response

from apps.patients.base_view.base_patients_view import BasePatientViewSet
from apps.staff.models import Department, StaffMember

from .models import (
    Patient,
    PatientAddress,
    PatientAllergies,
    PatientAppointment,
    PatientChronicConditions,
    PatientDemographics,
    PatientDiagnosis,
    PatientMedicalReport,
    PatientOperation,
    PatientPrescription,
    PatientVisit,
)
from .permissions import ROLE_PERMISSIONS
from .serializers import (
    CompletePatientSerializer,
    PatientAddressSerializer,
    PatientAllergySerializer,
    PatientAppointmentCreateSerializer,
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
from .services import AppointmentService, OperationService


class PatientViewSet(BasePatientViewSet):
    """ViewSet for Patient model with role-based permissions."""

    serializer_class = CompletePatientSerializer

    def get_queryset(self):
        return Patient.objects.select_related(
            "demographics", "emergency_contact"
        ).prefetch_related(
            "addresses", "allergies", "chronic_conditions", "medical_reports"
        )

    def get_object(self):
        """Override get_object to use get_object_or_404."""
        queryset = self.get_queryset()
        obj = self.get_object_or_404(queryset, id=self.kwargs["pk"])
        self.check_object_permissions(self.request, obj)
        return obj

    @action(detail=True, methods=["patch"], url_path="update-demographics")
    def update_demographics(self, request, pk=None):
        """Update patient demographics with permission check."""
        patient = self.get_object()
        user_role = request.user.role
        permissions = ROLE_PERMISSIONS.get(user_role, {})

        if "change" not in permissions.get("patientdemographics", []):
            return self.error_response(
                message="You don't have permission to update demographics",
                status_code=status.HTTP_403_FORBIDDEN,
            )

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
        user_role = request.user.role
        permissions = ROLE_PERMISSIONS.get(user_role, {})

        if "add" not in permissions.get("patientallergy", []):
            return self.error_response(
                message="You don't have permission to add allergies",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        serializer = PatientAllergySerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save(patient=patient)
        return self.success_response(data=serializer.data, message="Allergy added successfully")

    @action(detail=True, methods=["post"], url_path="add-chronic-condition")
    def add_chronic_condition(self, request, pk=None):
        """Add chronic condition to patient with permission check."""
        patient = self.get_object()
        user_role = request.user.role
        permissions = ROLE_PERMISSIONS.get(user_role, {})

        if "add" not in permissions.get("patientchroniccondition", []):
            return self.error_response(
                message="You don't have permission to add chronic conditions",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        serializer = PatientChronicConditionSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save(patient=patient)
        return self.success_response(data=serializer.data, message="Chronic condition added successfully")

    @action(detail=True, methods=["post"], url_path="update-emergency-contact")
    def update_emergency_contact(self, request, pk=None):
        """Update or create emergency contact with permission check."""
        patient = self.get_object()
        user_role = request.user.role
        permissions = ROLE_PERMISSIONS.get(user_role, {})

        if "change" not in permissions.get("patientemergencycontact", []):
            return self.error_response(
                message="You don't have permission to update emergency contact",
                status_code=status.HTTP_403_FORBIDDEN,
            )

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


class PatientAllergyViewSet(BasePatientViewSet):
    """ViewSet for PatientAllergy model with role-based permissions."""

    serializer_class = PatientAllergySerializer


    def get_queryset(self):
        return PatientAllergies.objects.filter(patient_id=self.kwargs.get("patient__pk"))

    def perform_create(self, serializer):
        serializer.save(patient_id=self.kwargs.get("patient__pk"))


class PatientChronicConditionViewSet(BasePatientViewSet):
    """ViewSet for PatientChronicCondition model with role-based permissions."""

    serializer_class = PatientChronicConditionSerializer


    def get_queryset(self):
        return PatientChronicConditions.objects.filter(
            patient_id=self.kwargs.get("patient__pk")
        )

    def perform_create(self, serializer):
        serializer.save(patient_id=self.kwargs.get("patient__pk"))


class PatientMedicalReportViewSet(BasePatientViewSet):
    serializer_class = PatientMedicalReportSerializer

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

class PatientVisitViewSet(BasePatientViewSet):
    """
    ViewSet for managing patient visits.
    """

    serializer_class = PatientVisitSerializer
    basename = "patientcisit"

    def get_queryset(self):
        return PatientVisit.objects.filter(patient_id=self.kwargs.get("patient__pk"))

    def perform_create(self, serializer):
        """
        Save the patient visit record.
        """
        serializer.save(patient_id=self.kwargs.get("patient__pk"))

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

class PatientDiagnosisViewSet(BasePatientViewSet):
    """
    ViewSet for managing patient diagnoses.
    """

    serializer_class = PatientDiagnosisSerializer

    def get_queryset(self):
        return PatientDiagnosis.objects.filter(patient_id=self.kwargs.get("patient__pk"))

    def perform_create(self, serializer):
        """
        Save the patient diagnosis record.
        """
        serializer.save(patient_id=self.kwargs.get("patient__pk"))

class PatientAppointmentViewSet(BasePatientViewSet):


    def get_queryset(self):
        patient_id = self.kwargs.get("patient__pk")
        return PatientAppointment.objects.filter(
            patient_id=patient_id
        ).select_related(
            "physician",
            "department",
            "patient",
            "created_by",
            "modified_by")

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return PatientAppointmentCreateSerializer
        return PatientAppointmentSerializer

    def perform_create(self, serializer):
        physician = serializer.validated_data.pop("physician")
        department = serializer.validated_data.pop("department")

        physician = StaffMember.objects.get(id=physician)
        department = Department.objects.get(id=department)

        AppointmentService.create_appointment(
            serializer,
            physician,
            department,
            self.request.user,
            self.kwargs.get("patient__pk")
        )

    def perform_update(self, serializer):
        AppointmentService.update_appointment(
            serializer,
            self.request.user
        )

    @action(detail=True, methods=["patch", "get"])
    def reschedule(self, request, patient__pk=None, pk=None):
        """
        Handle appointment rescheduling for a specific patient.

        Args:
            request: The HTTP request object
            patient__pk: Patient's primary key
            pk: Appointment's primary key

        Returns:
            Response with updated appointment data or error messages

        """
        try:
            appointment = self.get_object()

            # Validate that appointment belongs to the specified patient
            if str(appointment.patient.pk) != str(patient__pk):
                return Response(
                    {"error": "Appointment does not belong to specified patient"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            serializer = self.get_serializer(
                appointment,
                data=request.data,
                partial=True
            )

            if serializer.is_valid():
                AppointmentService.update_appointment(
                    serializer,
                    self.request.user
                )
                return Response(serializer.data, status=status.HTTP_202_ACCEPTED)

            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        except (ValidationError, NotFound) as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
class PrescriptionViewSet(BasePatientViewSet):
    """
    A viewset for managing Prescription instances with optimized querying.

    Supports both patient-specific and individual prescription retrieval.
    """

    serializer_class = PrescriptionSerializer


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

