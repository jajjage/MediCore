# urls.py
from django.urls import include, path
from rest_framework_nested import routers

from .views import (
    PatientAddressViewSet,
    PatientAllergyViewSet,
    PatientChronicConditionViewSet,
    PatientDemographicsViewSet,
    PatientMedicalReportViewSet,
    PatientViewSet,
)

# Parent router for patients
router = routers.DefaultRouter()
router.register(r"patients", PatientViewSet, basename="patient")

# Nested router for patient demographics
demographics_router = routers.NestedSimpleRouter(router, r"patients", lookup="patient")
demographics_router.register(
    r"demographics", PatientDemographicsViewSet, basename="patient-demographics"
)

# Nested router for patient addresses
address_router = routers.NestedSimpleRouter(router, r"patients", lookup="patient")
address_router.register(
    r"addresses", PatientAddressViewSet, basename="patient-addresses"
)

# Nested router for patient allergies
allergy_router = routers.NestedSimpleRouter(router, r"patients", lookup="patient")
allergy_router.register(
    r"allergies", PatientAllergyViewSet, basename="patient-allergies"
)

# Nested router for patient chronic conditions
condition_router = routers.NestedSimpleRouter(router, r"patients", lookup="patient")
condition_router.register(
    r"conditions", PatientChronicConditionViewSet, basename="patient-conditions"
)

# Nested router for patient medical reports
report_router = routers.NestedSimpleRouter(router, r"patients", lookup="patient")
report_router.register(
    r"reports", PatientMedicalReportViewSet, basename="patient-medical-report"
)

urlpatterns = [
    path("", include(router.urls)),
    path("", include(demographics_router.urls)),
    path("", include(address_router.urls)),
    path("", include(allergy_router.urls)),
    path("", include(condition_router.urls)),
    path("", include(report_router.urls)),
]
