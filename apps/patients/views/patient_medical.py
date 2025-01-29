from apps.patients.models import (
    PatientAllergies,
    PatientChronicCondition,
)
from apps.patients.serializers import (
    PatientAllergySerializer,
    PatientChronicConditionSerializer,
)
from base_view import BaseViewSet


class PatientAllergyViewSet(BaseViewSet):
    """ViewSet for PatientAllergy model with role-based permissions."""

    serializer_class = PatientAllergySerializer


    def get_queryset(self):
        return PatientAllergies.objects.filter(patient_id=self.kwargs.get("patient__pk"))

    def perform_create(self, serializer):
        serializer.save(patient_id=self.kwargs.get("patient__pk"))


class PatientChronicConditionViewSet(BaseViewSet):
    """ViewSet for PatientChronicCondition model with role-based permissions."""

    serializer_class = PatientChronicConditionSerializer


    def get_queryset(self):
        return PatientChronicCondition.objects.filter(
            patient_id=self.kwargs.get("patient__pk")
        )

    def perform_create(self, serializer):
        serializer.save(patient_id=self.kwargs.get("patient__pk"))
