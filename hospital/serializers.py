from rest_framework import serializers

from core.serializers import AdminUserSerializer
from tenants.serializers import TenantSerializer

from .models import HospitalProfile


class HospitalProfileSerializer(serializers.ModelSerializer):
    tenant = TenantSerializer(read_only=True)
    admin_user = AdminUserSerializer(read_only=True)

    class Meta:
        model = HospitalProfile
        fields = [
            "tenant",
            "admin_user",
            "hospital_name",
            "hospital_code",
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
    tenant_name = serializers.CharField(max_length=100)
    paid_until = serializers.DateField()
    on_trial = serializers.BooleanField(default=True)

    # Admin user data
    admin_email = serializers.EmailField()
    admin_password = serializers.CharField( write_only=True)
    admin_first_name = serializers.CharField( write_only=True)
    admin_last_name = serializers.CharField( write_only=True)
    admin_phone_number = serializers.CharField( write_only=True)

    # Hospital profile data
    hospital_name = serializers.CharField(max_length=200)
    hospital_code = serializers.CharField(max_length=4)
    license_number = serializers.CharField(max_length=100)
    contact_email = serializers.EmailField()
    contact_phone = serializers.CharField(max_length=20)
    subscription_plan = serializers.CharField(max_length=20)
    address = serializers.CharField(required=False, allow_blank=True)
    specialty = serializers.CharField(required=False, allow_blank=True)
    bed_capacity = serializers.IntegerField(required=False, allow_null=True)

