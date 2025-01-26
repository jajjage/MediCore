from .patient_appointment import PatientAppointmentViewSet
from .patient_diagnosis import PatientDiagnosisViewSet
from .patient_medical import PatientAllergyViewSet, PatientChronicConditionViewSet
from .patient_operation import PatientOperationViewSet
from .patient_prescription import PatientPrescriptionViewSet
from .patient_report import PatientMedicalReportViewSet
from .patient_visit import PatientVisitViewSet
from .patients import PatientDemographicsViewSet, PatientViewSet, UserCreateView

__all__ = [
    "PatientAllergyViewSet",
    "PatientAppointmentViewSet",
    "PatientChronicConditionViewSet",
    "PatientDemographicsViewSet",
    "PatientDiagnosisViewSet",
    "PatientMedicalReportViewSet",
    "PatientOperationViewSet",
    "PatientPrescriptionViewSet",
    "PatientViewSet",
    "PatientVisitViewSet",
    "UserCreateView",
]
