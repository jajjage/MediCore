from rest_framework.generics import ListAPIView

from .models import Department, DepartmentMember
from .permissions import TenantModelPermission
from .serializers import DepartmentDoctorSerializer, DepartmentListSerializer


class ClinicalDepartmentListView(ListAPIView):
    serializer_class = DepartmentListSerializer
    permission_classes = [TenantModelPermission]
    queryset = Department.objects.all()
    name= "department"


class DepartmentDoctorsView(ListAPIView):
    serializer_class = DepartmentDoctorSerializer
    permission_classes = [TenantModelPermission]
    name = "departmentmember"

    def get_queryset(self):
        department_id = self.kwargs.get("department_id")
        return DepartmentMember.objects.filter(
            department_id=department_id,  # Directly use the `department` field
            role="DOCTOR",               # Use the appropriate choice for the `role` field
            is_active=True
        ).order_by("user__first_name")

