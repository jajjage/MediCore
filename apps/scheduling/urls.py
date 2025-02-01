from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ShiftTemplateViewSet

router = DefaultRouter()
router.register(r"shift-templates", ShiftTemplateViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
