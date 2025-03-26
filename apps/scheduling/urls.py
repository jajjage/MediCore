from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ShiftGenerationViewSet, ShiftTemplateViewSet

router = DefaultRouter()
router.register(r"shift-templates", ShiftTemplateViewSet)
router.register(r"generate-shifts", ShiftGenerationViewSet, basename="shifts")


urlpatterns = [
    path("", include(router.urls)),
]
