# urls.py
from django.urls import include, path
from rest_framework_nested import routers  # type: ignore

from .views import PatientAddressViewSet, PatientDemographicsViewSet, PatientViewSet

# Create main router
router = routers.DefaultRouter()
router.register(r"patients", PatientViewSet, basename="patient")

# Create nested routers
patient_router = routers.NestedDefaultRouter(router, r"patients", lookup="patient")
patient_router.register(r"demographics", PatientDemographicsViewSet, basename="patient-demographics")
patient_router.register(r"addresses", PatientAddressViewSet, basename="patient-addresses")

urlpatterns = [
    path("", include(router.urls)),
    path("", include(patient_router.urls)),
]
