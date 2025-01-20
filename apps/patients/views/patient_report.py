
from rest_framework.exceptions import NotFound

from apps.patients.base_view.base_patients_view import BasePatientViewSet
from apps.patients.models import (
    PatientMedicalReport,
)
from apps.patients.serializers import (
    PatientMedicalReportSerializer,
)


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
