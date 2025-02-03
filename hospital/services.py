import re
import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction

from core.models import HospitalMembership
from tenants.models import Client, Domain

from .models import HospitalProfile, Role


def generate_schema_name(hospital_name: str, max_length: int = 63) -> str:
    """
    Generate a PostgreSQL-compatible schema name using hospital name and UUID.

    Args:
        hospital_name: Name of the hospital
        max_length: Maximum length for PostgreSQL schema name (default 63)

    Returns:
        A sanitized, unique schema name

    """
    # Sanitize hospital name: lowercase, remove special chars, limit length
    clean_name = re.sub(r"[^a-zA-Z0-9]", "", hospital_name.lower())
    clean_name = clean_name[:20]  # Limit hospital name portion

    # Generate short UUID (first 8 chars)
    unique_id = str(uuid.uuid4())[:8]

    # Combine parts with underscore
    schema_name = f"{clean_name}_{unique_id}"

    # Ensure final length is within PostgreSQL limits
    if len(schema_name) > max_length:
        schema_name = schema_name[:max_length]

    # Ensure name starts with letter (PostgreSQL requirement)
    if not schema_name[0].isalpha():
        schema_name = f"h_{schema_name}"[:(max_length)]

    return schema_name

class TenantCreationService:
    @staticmethod
    def add_initial_member(member, tenant, hospital_profile):
        """Add initial member for the tenant admin."""
        # Create admin permission for the tenant
        role = Role.objects.get(name="Tenant Admin")
        hospital_membership = HospitalMembership.objects.create(
            user=member,
            tenant=tenant,
            hospital_profile=hospital_profile,
            role=role,
            is_tenant_admin=True,
        )
        return hospital_membership

    @staticmethod
    @transaction.atomic
    def create_tenant(validated_data):
        user_model = get_user_model()

        # Create tenant
        tenant = Client.objects.create(
            schema_name=generate_schema_name(validated_data["hospital_name"]),
            name=validated_data["tenant_name"],
            paid_until=validated_data["paid_until"],
            on_trial=validated_data.get("on_trial", True),
            status="active"  # Set initial status
        )


        # Create domain
        domain_name = (
            f"{validated_data['hospital_name'].lower().replace(' ', '-')}"
            f".{settings.BASE_DOMAIN}"
        )
        Domain.objects.create(domain=domain_name, tenant=tenant, is_primary=True)

        # Create admin user
        member = user_model.objects.create_user(
            email=validated_data["admin_email"],
            password=validated_data["admin_password"],
            first_name=validated_data["admin_first_name"],
            last_name=validated_data["admin_last_name"],
            phone_number=validated_data["admin_phone_number"],
            is_staff=True,
        )
        # Create hospital profile
        hospital_profile = HospitalProfile.objects.create(
            tenant=tenant,
            hospital_name=validated_data["hospital_name"],
            hospital_code=validated_data["hospital_code"].upper(),
            license_number=validated_data["license_number"],
            contact_email=validated_data["contact_email"],
            contact_phone=validated_data["contact_phone"],
            subscription_plan=validated_data["subscription_plan"],
            address=validated_data.get("address", ""),
            specialty=validated_data.get("specialty", ""),
            bed_capacity=validated_data.get("bed_capacity"),
        )
        # Setup initial permissions

        TenantCreationService.add_initial_member(member, tenant, hospital_profile)

        return hospital_profile

