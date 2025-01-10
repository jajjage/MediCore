from django.urls import path

from .views import ClinicalDepartmentListView, DepartmentDoctorsView

urlpatterns = [
    path("departments/",
         ClinicalDepartmentListView.as_view(),
         name="department"),
    path("departments/members/<str:department_id>/doctors/",
         DepartmentDoctorsView.as_view(),
         name="departmentmember"),
]
