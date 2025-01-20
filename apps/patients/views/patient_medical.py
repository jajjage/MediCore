from apps.patients.base_view.base_patients_view import BasePatientViewSet
from apps.patients.models import (
    PatientAllergies,
    PatientChronicConditions,
)
from apps.patients.serializers import (
    PatientAllergySerializer,
    PatientChronicConditionSerializer,
)


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
