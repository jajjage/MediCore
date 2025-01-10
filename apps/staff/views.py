from rest_framework.generics import ListAPIView

from .models import Department, DepartmentMember
from .permissions import AppointmentRolePermission
from .serializers import DepartmentDoctorSerializer, DepartmentListSerializer


class ClinicalDepartmentListView(ListAPIView):
    serializer_class = DepartmentListSerializer
    permission_classes = [AppointmentRolePermission]
    name= "department"

    print("the view")
    def get_queryset(self):
        return Department.objects.filter(
            department_type="CLINICAL"
        ).order_by("name")

class DepartmentDoctorsView(ListAPIView):
    serializer_class = DepartmentDoctorSerializer
    permission_classes = [AppointmentRolePermission]
    name = "departmentmember"

    def get_queryset(self):
        department_id = self.kwargs.get("department_id")
        return DepartmentMember.objects.filter(
            department_id=department_id,  # Directly use the `department` field
            role="DOCTOR",               # Use the appropriate choice for the `role` field
            is_active=True
        ).order_by("user__first_name")

