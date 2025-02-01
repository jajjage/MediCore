from django_filters import rest_framework as filters

from apps.staff.models import (
    Department,
    DepartmentMember,
    DoctorProfile,
    NurseProfile,
    StaffTransfer,
    TechnicianProfile,
    WorkloadAssignment,
)


class WorkloadAssignmentFilter(filters.FilterSet):
    department_member = filters.ModelChoiceFilter(queryset=DepartmentMember.objects.all())

    class Meta:
        model = WorkloadAssignment
        fields = ["department_member"]

class StaffTransferFilter(filters.FilterSet):
    transfer_type = filters.TypedChoiceFilter(choices=[
        ("PERMANENT", "Permanent Transfer"),
        ("TEMPORARY", "Temporary Cover"),
        ("ROTATION", "Rotation"),
        ("EMERGENCY", "Emergency Reassignment")
    ])
    effective_date = filters.DateFromToRangeFilter()

    class Meta:
        model = StaffTransfer
        fields = ["transfer_type", "effective_date", "from_assignment", "to_assignment"]

class ProfileFilter(filters.FilterSet):
    years_of_experience = filters.NumberFilter()
    years_of_experience_gt = filters.NumberFilter(field_name="years_of_experience", lookup_expr="gt")
    years_of_experience_lt = filters.NumberFilter(field_name="years_of_experience", lookup_expr="lt")

    class Meta:
        abstract = True
        fields = ["qualification", "years_of_experience", "certification_number"]

class DoctorProfileFilter(ProfileFilter):
    class Meta(ProfileFilter.Meta):
        model = DoctorProfile
        fields = (*ProfileFilter.Meta.fields, "specialization", "license_number")

class NurseProfileFilter(ProfileFilter):
    class Meta(ProfileFilter.Meta):
        model = NurseProfile
        fields =(*ProfileFilter.Meta.fields, "nurse_license", "ward_specialty")

class TechnicianProfileFilter(ProfileFilter):
    class Meta(ProfileFilter.Meta):
        model = TechnicianProfile
        fields = (*ProfileFilter.Meta.fields, "technician_license")


class DepartmentFilter(filters.FilterSet):
    name = filters.CharFilter(lookup_expr="icontains")
    code = filters.CharFilter(lookup_expr="icontains")
    department_type = filters.TypedChoiceFilter(
        choices=Department.DEPARTMENT_TYPES,
        required=False
    )
    parent_department = filters.ModelChoiceFilter(
        queryset=Department.objects.all(),
        required=False
    )
    created_at = filters.DateTimeFromToRangeFilter()
    is_active = filters.BooleanFilter()

    class Meta:
        model = Department
        fields = [
            "name",
            "code",
            "department_type",
            "parent_department",
            "created_at",
            "is_active"
        ]

# class StaffMemberFilter(filters.FilterSet):
#     name = filters.CharFilter(method="filter_by_name")
#     # role = filters.ModelChoiceFilter(queryset=StaffRole.objects.all())
#     # department = filters.ModelChoiceFilter(
#     #     queryset=Department.objects.all(),
#     #     method="filter_by_department"
#     # )

#     class Meta:
#         model = StaffMember
#         fields = ["name"]

#     def filter_by_name(self, queryset, name, value):
#         return queryset.filter(
#             Q(first_name__icontains=value) |
#             Q(last_name__icontains=value)
#         )

#     def filter_by_department(self, queryset, name, value):
#         return queryset.filter(department_memberships__department=value)
