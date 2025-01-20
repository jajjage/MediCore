

from apps.patients.base_view.base_patients_view import BasePatientViewSet
from apps.patients.models import (
    PatientDiagnosis,
)
from apps.patients.serializers import (
    PatientDiagnosisSerializer,
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
