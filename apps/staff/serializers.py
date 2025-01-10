from django.contrib.auth import get_user_model
from djoser.serializers import UserCreateSerializer, UserSerializer
from rest_framework import serializers

from .models import Department, DepartmentMember, StaffMember, StaffRole

User = get_user_model()

# class PublicStaffCreateSerializer(UserCreateSerializer):
#     class Meta(UserCreateSerializer.Meta):
#         model = Staff
#         fields = ('id', 'email', 'password', 'first_name', 'last_name')


class TenantStaffCreateSerializer(UserCreateSerializer):
    department = serializers.PrimaryKeyRelatedField(queryset=Department.objects.all())
    role = serializers.PrimaryKeyRelatedField(queryset=StaffRole.objects.all())

    class Meta(UserCreateSerializer.Meta):
        model = StaffMember
        fields = (
            "id",
            "email",
            "password",
            "first_name",
            "last_name",
            "department",
            "role",
        )


# class PublicStaffSerializer(UserSerializer):
#     class Meta(UserSerializer.Meta):
#         model = Staff
#         fields = ('id', 'email', 'first_name', 'last_name')


class StaffSerializer(UserSerializer):
    class Meta(UserSerializer.Meta):
        model = StaffMember
        fields = ("id", "email", "first_name", "last_name", "department", "role")
        read_only_fields = ("email",)


class DepartmentListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ["id", "name", "department_type"]

class DepartmentDoctorSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = DepartmentMember
        fields = ["id", "full_name", "department"]

    def get_full_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}"
