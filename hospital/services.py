import re
import uuid

from django.apps import apps
from django.conf import settings
from django.db import connection, transaction

from tenants.models import Client, Domain

from .models import HospitalProfile


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
    def get_user_model():
        if connection.schema_name == "public":
            return apps.get_model("core", "MyUser")
        return apps.get_model("staff", "StaffMember")

    @staticmethod
    @transaction.atomic
    def create_tenant(validated_data):
        User = TenantCreationService.get_user_model()  # noqa: N806

        # Log the selected User model for debugging

        # Create tenant
        tenant = Client.objects.create(
            schema_name=generate_schema_name(validated_data["hospital_name"]),
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
