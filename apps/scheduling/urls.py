from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    NurseAvailabilityViewSet,
    ShiftGenerationViewSet,
    ShiftTemplateViewSet,
    UserShiftPreferenceViewSet,
)

router = DefaultRouter()
router.register(r"shift-templates", ShiftTemplateViewSet)
router.register(r"generate-shifts", ShiftGenerationViewSet, basename="shifts")
router.register(r"nurse-availability", NurseAvailabilityViewSet, basename="nurse-availability")
router.register(r"shift-preferences", UserShiftPreferenceViewSet, basename="user-shift-preference")


urlpatterns = [
    path("", include(router.urls)),
]
