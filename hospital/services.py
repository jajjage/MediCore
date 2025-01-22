import re
import uuid

from django.apps import apps
from django.conf import settings
from django.db import connection, transaction

from core.models import TenantMembership
from tenants.models import Client, Domain

from .models import HospitalProfile, HospitalStaffMembership


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
        """Get the appropriate user model based on schema."""
        if connection.schema_name == "public":
            return apps.get_model("core", "MyUser")
        return apps.get_model("staff", "StaffMember")

    @staticmethod
    def add_hospital_membership(hospital, user):
        """
        Add a staff member to the hospital profile and ensure tenant association.
        """
        # Create the membership record explicitly
        HospitalStaffMembership.objects.create(
            hospital=hospital,
            user=user,
            is_active=True
        )

    @staticmethod
    def setup_initial_permissions(tenant, admin_user):
        """ASetup initial permissions for the tenant admin."""
        # Create admin permission for the tenant
        tenant_membership = TenantMembership.objects.create(
            user=admin_user,
            tenant=tenant,
            role="ADMIN"
        )
        return tenant_membership

    @staticmethod
    @transaction.atomic
    def create_tenant(validated_data):
        user_model = TenantCreationService.get_user_model()

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
        admin_user = user_model.objects.create_tenant_admin(
            email=validated_data["admin_email"],
            password=validated_data["admin_password"],
            first_name=validated_data["admin_first_name"],
            last_name=validated_data["admin_last_name"],
            phone_number=validated_data["admin_phone_number"],
        )

        # Setup initial permissions
        TenantCreationService.setup_initial_permissions(tenant, admin_user)

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
        TenantCreationService.add_hospital_membership(hospital_profile, admin_user)
        return hospital_profile

    @staticmethod
    @transaction.atomic
    def add_user_to_tenant(user, tenant, role="VIEWER"):
        """
        Add a user to a tenant with specified permissions.

        Args:
            user: The user to add
            tenant: The tenant to add the user to
            role: The type of permission to grant (ADMIN, STAFF, or VIEWER)

        """
        # Validate permission type
        if role not in ["ADMIN", "STAFF", "VIEWER"]:
            raise ValueError("Invalid permission type")

        tenant_membership = TenantMembership.objects.create(
            user=user,
            tenant=tenant,
            role=role
        )

        return tenant_membership

    @staticmethod
    @transaction.atomic
    def remove_user_from_tenant(user, tenant):
        """
        Remove a user's access to a tenant.

        Args:
            user: The user to remove
            tenant: The tenant to remove the user from

        """
        # Delete permission
        TenantMembership.objects.filter(
            user=user,
            tenant=tenant
        ).delete()


    @staticmethod
    def get_tenant_users(tenant, role=None):
        """
        Get all users with access to a tenant, optionally filtered by permission type.

        Args:
            tenant: The tenant to get users for
            role: Optional permission type to filter by

        """
        query = TenantMembership.objects.filter(tenant_id=tenant.id)
        if role:
            query = query.filter(role=role)
        return query.select_related("user")
