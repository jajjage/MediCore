

from apps.patients.models import (
    PatientDiagnoses,
)
from apps.patients.serializers import (
    PatientDiagnosisSerializer,
)
from base_view import BaseViewSet


class PatientDiagnosisViewSet(BaseViewSet):
    """
    ViewSet for managing patient diagnoses.
    """

    serializer_class = PatientDiagnosisSerializer

    def get_queryset(self):
        return PatientDiagnoses.objects.filter(patient_id=self.kwargs.get("patient__pk"))

    def perform_create(self, serializer):
        """
        Save the patient diagnosis record.
        """
        serializer.save(patient_id=self.kwargs.get("patient__pk"))
