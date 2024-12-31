from django.db import transaction
from django.conf import settings
from tenants.models import Client, Domain
from django.contrib.auth import get_user_model
from .models import HospitalProfile
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


class TenantCreationService:
    @staticmethod
    @transaction.atomic
    def create_tenant(validated_data):
        try:
            # Step 1: Create tenant
            tenant = Client.objects.create(
                schema_name=validated_data["schema_name"],
                name=validated_data["tenant_name"],
                paid_until=validated_data["paid_until"],
                on_trial=validated_data.get("on_trial", True),
            )

            # Step 2: Create domain
            domain_name = (
                f"{validated_data['hospital_name'].lower().replace(' ', '-')}"
                f".{settings.BASE_DOMAIN}"
            )
            Domain.objects.create(domain=domain_name, tenant=tenant, is_primary=True)

            # Step 3: Create admin user
            admin_user = User.objects.create_tenant_admin(
                email=validated_data["admin_email"],
                password=validated_data["admin_password"],
                hospital=tenant,
                
            )

            # Step 4: Create hospital profile
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

        except Exception as e:
            logger.error(f"Failed to create tenant: {str(e)}", exc_info=True)
            raise
