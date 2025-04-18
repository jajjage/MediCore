# urls.py
from django.urls import include, path
from rest_framework_nested import routers

from .views import (
    PatientAllergyViewSet,
    PatientAppointmentViewSet,
    PatientChronicConditionViewSet,
    PatientDemographicsViewSet,
    PatientDiagnosisViewSet,
    PatientMedicalReportViewSet,
    PatientOperationViewSet,
    PatientPrescriptionViewSet,
    PatientViewSet,
    PatientVisitViewSet,
    UserCreateView,
)

# Parent router for patients
router = routers.DefaultRouter()
router.register(r"patients", PatientViewSet, basename="patient")

# Nested router for patient demographics
demographics_router = routers.NestedSimpleRouter(router, r"patients", lookup="patient")
demographics_router.register(
    r"demographics", PatientDemographicsViewSet, basename="patient-demographics"
)


# Nested router for patient allergies
allergy_router = routers.NestedSimpleRouter(router, r"patients", lookup="patient")
allergy_router.register(
    r"allergies", PatientAllergyViewSet, basename="patient-allergies"
)

# Nested router for patient chronic conditions
condition_router = routers.NestedSimpleRouter(router, r"patients", lookup="patient")
condition_router.register(
    r"conditions", PatientChronicConditionViewSet, basename="patient-chronic-conditions"
)

# Nested router for patient medical reports
report_router = routers.NestedSimpleRouter(router, r"patients", lookup="patient")
report_router.register(
    r"reports", PatientMedicalReportViewSet, basename="patient-medical-report"
)

visit_router = routers.NestedSimpleRouter(router, r"patients", lookup="patient")
visit_router.register(
    r"visits", PatientVisitViewSet, basename="patient-visit"
)

operation_router = routers.NestedSimpleRouter(router, r"patients", lookup="patient")
operation_router.register(
    r"operations", PatientOperationViewSet, basename="patient-operation"
)

appointment_router = routers.NestedSimpleRouter(router, r"patients", lookup="patient")
appointment_router.register(
    r"appointments", PatientAppointmentViewSet, basename="patient-appointment"
)

diagnosis_router = routers.NestedSimpleRouter(router, r"patients", lookup="patient")
diagnosis_router.register(
    r"diagnosis", PatientDiagnosisViewSet, basename="patient-diagnosis"
)
prescription_router = routers.NestedSimpleRouter(router, r"patients", lookup="patient")
prescription_router.register(
    r"prescriptions", PatientPrescriptionViewSet, basename="patient-prescription"
)



urlpatterns = [
    path("register/", UserCreateView.as_view(), name = "my-user"),
    path("", include(router.urls)),
    path("", include(demographics_router.urls)),
    path("", include(allergy_router.urls)),
    path("", include(condition_router.urls)),
    path("", include(report_router.urls)),
    path("", include(visit_router.urls)),
    path("", include(operation_router.urls)),
    path("", include(appointment_router.urls)),
    path("", include(diagnosis_router.urls)),
    path("", include(prescription_router.urls)),
]
