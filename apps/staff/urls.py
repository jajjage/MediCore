from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("departments", views.DepartmentViewSet, basename="department")
# router.register("staff-members", views.StaffMemberViewSet, basename="staff-member")
router.register("department-members", views.DepartmentMemberViewSet, basename="department-member")
router.register("workload-assignments", views.WorkloadAssignmentViewSet, basename="workload-assignment")
router.register("staff-transfers", views.StaffTransferViewSet, basename="staff-transfer")
router.register("doctor-profiles", views.DoctorProfileViewSet, basename="doctor-profile")
router.register("nurse-profiles", views.NurseProfileViewSet, basename="nurse-profile")
router.register("technician-profiles", views.TechnicianProfileViewSet, basename="technician-profile")

urlpatterns = [
    path("", include(router.urls)),
]
