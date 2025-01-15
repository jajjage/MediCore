import uuid

from django.apps import apps
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from tenants.models import Client


class HospitalStaffMembership(models.Model):
    """Through model for hospital staff membership with additional metadata."""

    hospital = models.ForeignKey("hospital.HospitalProfile", on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    tenant_permission = models.ForeignKey(
        "core.TenantPermission",
        on_delete=models.CASCADE,
        help_text="The staff member's role and permissions in this hospital"
    )
    joined_date = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "hospital_staff_membership"
        unique_together = ("hospital", "user")

    def __str__(self):
        return (
            f"{self.user.email} - "
            f"{self.tenant_permission.get_permission_type_display()} at "
            f"{self.hospital.hospital_name}"
        )

    def clean(self):
        if self.user == self.hospital.admin_user:
            raise ValidationError("Cannot create membership for primary admin")

        if self.user.hospital != self.hospital.tenant:
            raise ValidationError("User must belong to the same tenant as the hospital")

        # Validate that the tenant_permission matches the hospital's tenant
        if self.tenant_permission.schema_name != self.hospital.tenant.schema_name:
            raise ValidationError(
                "Tenant permission must be for the same tenant as the hospital"
            )
class HospitalProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.OneToOneField(
        "tenants.Client",
        on_delete=models.CASCADE,
        related_name="profile")

    admin_user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="administered_hospital"
    )
    additional_staff = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="HospitalStaffMembership",
        related_name="associated_hospitals",
        blank=True
    )

    SUBSCRIPTION_CHOICES = [
        ("trial", "Trial"),
        ("basic", "Basic"),
        ("premium", "Premium"),
    ]
    subscription_plan = models.CharField(max_length=20, choices=SUBSCRIPTION_CHOICES)
    hospital_name = models.CharField(max_length=200)
    license_number = models.CharField(max_length=100, unique=True)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=20)

    # Add additional useful fields
    address = models.TextField(blank=True)
    specialty = models.CharField(max_length=100, blank=True)
    bed_capacity = models.PositiveIntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "hospital_profile"

    def __str__(self):
        return self.hospital_name


    def clean(self):
        super().clean()

        if self.tenant_id and self.pk is None and Client.objects.filter(schema_name=self.tenant.schema_name).exists():
            raise ValidationError(
                {"tenant": "A tenant with this schema name already exists."}
            )

        User = apps.get_model(settings.AUTH_USER_MODEL.split(".")[0],
                            settings.AUTH_USER_MODEL.split(".")[1])

        if User.objects.filter(email=self.contact_email).exists():
            raise ValidationError(
                {"contact_email": "A user with this email already exists."}
            )

        if (
            HospitalProfile.objects.filter(license_number=self.license_number)
            .exclude(pk=self.pk)
            .exists()
        ):
            raise ValidationError(
                {"license_number": "This license number is already registered."}
            )

    def add_staff_member(self, user):
        """
        Add a staff member to the hospital profile and ensure tenant association.
        """
        if user.hospital != self.tenant:
            raise ValidationError(
                "User's tenant must match the hospital profile's tenant"
            )

        if hasattr(user, "administered_hospital") and user.administered_hospital != self:
            raise ValidationError(
                "User is already an admin for another hospital"
            )

        if hasattr(user, "associated_hospitals") and \
        user.associated_hospitals.exclude(id=self.id).exists():
            raise ValidationError(
                "User is already associated with another hospital"
            )

        # Get or create the tenant permission
        TenantPermission = apps.get_model("core", "TenantPermission")
        tenant_permission, _ = TenantPermission.objects.get_or_create(
            user=user,
            schema_name=self.tenant.schema_name,
            defaults={"permission_type": "STAFF"}
        )

        # Create the membership record explicitly
        HospitalStaffMembership.objects.create(
            hospital=self,
            user=user,
            tenant_permission=tenant_permission,
            is_active=True
        )

    def remove_staff_member(self, user):
        """Remove a staff member from the hospital profile."""
        if user == self.admin_user:
            raise ValidationError("Cannot remove primary admin user")

        HospitalStaffMembership.objects.filter(
            hospital=self,
            user=user
        ).delete()

    def get_staff_by_role(self, role):
        """Get all staff members with a specific role."""
        return self.additional_staff.filter(
            hospitalstaffmembership__role=role
        )

    def get_all_staff(self):
        """Get all staff members including the primary admin."""
        User = apps.get_model(settings.AUTH_USER_MODEL.split(".")[0],
                            settings.AUTH_USER_MODEL.split(".")[1])
        return User.objects.filter(
            models.Q(id=self.admin_user.id) |
            models.Q(id__in=self.additional_staff.all())
        ).distinct()
