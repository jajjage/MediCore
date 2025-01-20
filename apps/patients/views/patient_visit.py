

from apps.patients.base_view.base_patients_view import BasePatientViewSet
from apps.patients.models import (
    PatientVisit,
)
from apps.patients.serializers import (
    PatientVisitSerializer,
)


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
