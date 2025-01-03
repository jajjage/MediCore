# urls.py
from django.urls import include, path
from rest_framework_nested import routers

from .views import PatientAddressViewSet, PatientDemographicsViewSet, PatientViewSet

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

urlpatterns = [
    path("", include(router.urls)),
    path("", include(demographics_router.urls)),
    path("", include(address_router.urls)),
]
