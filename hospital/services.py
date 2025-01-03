from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from .models import HospitalProfile
from tenants.models import Client, Domain
from django.db import connection, transaction


class TenantCreationService:
    @staticmethod
    def get_user_model():
        if connection.schema_name == "public":
            return apps.get_model("core", "MyUser")
        return apps.get_model("staff", "StaffMember")

    @staticmethod
    @transaction.atomic
    def create_tenant(validated_data):
        User = TenantCreationService.get_user_model()

        # Log the selected User model for debugging
        print(f"Using User model: {User}")

        # Create tenant
        tenant = Client.objects.create(
            schema_name=validated_data["schema_name"],
            name=validated_data["tenant_name"],
            paid_until=validated_data["paid_until"],
            on_trial=validated_data.get("on_trial", True),
        )

        # Create domain
        domain_name = (
            f"{validated_data['hospital_name'].lower().replace(' ', '-')}"
            f".{settings.BASE_DOMAIN}"
        )
        Domain.objects.create(domain=domain_name, tenant=tenant, is_primary=True)

        # Create admin user
        admin_user = User.objects.create_tenant_admin(
            email=validated_data["admin_email"],
            password=validated_data["admin_password"],
            hospital=tenant,
        )

        # Create hospital profile
        hospital_profile = HospitalProfile.objects.create(
            tenant=tenant,
            admin_user=admin_user,
            hospital_name=validated_data["hospital_name"],
            license_number=validated_data["license_number"],
            contact_email=validated_data["contact_email"],
            contact_phone=validated_data["contact_phone"],
            subscription_plan=validated_data["subscription_plan"],
            address=validated_data.get("address", ""),
            specialty=validated_data.get("specialty", ""),
            bed_capacity=validated_data.get("bed_capacity"),
        )

        return hospital_profile
