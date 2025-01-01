from rest_framework import serializers
from .models import HospitalProfile
from tenants.serializers import TenantSerializer
from core.serializers import AdminUserSerializer


class HospitalProfileSerializer(serializers.ModelSerializer):
    tenant = TenantSerializer(read_only=True)
    admin_user = AdminUserSerializer(read_only=True)

    class Meta:
        model = HospitalProfile
        fields = [
            "tenant",
            "admin_user",
            "hospital_name",
            "license_number",
            "contact_email",
            "contact_phone",
            "subscription_plan",
            "address",
            "specialty",
            "bed_capacity",
        ]


class CreateTenantRequestSerializer(serializers.Serializer):
    # Tenant data
    schema_name = serializers.CharField(max_length=100)
    tenant_name = serializers.CharField(max_length=100)
    paid_until = serializers.DateField()
    on_trial = serializers.BooleanField(default=True)

    # Admin user data
    admin_email = serializers.EmailField()
    admin_password = serializers.CharField(min_length=8, write_only=True)

    # Hospital profile data
    hospital_name = serializers.CharField(max_length=200)
    license_number = serializers.CharField(max_length=100)
    contact_email = serializers.EmailField()
    contact_phone = serializers.CharField(max_length=20)
    subscription_plan = serializers.CharField(max_length=20)
    address = serializers.CharField(required=False, allow_blank=True)
    specialty = serializers.CharField(required=False, allow_blank=True)
    bed_capacity = serializers.IntegerField(required=False, allow_null=True)
