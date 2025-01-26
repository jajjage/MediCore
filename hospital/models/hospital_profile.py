import uuid

from django.apps import apps
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import models, transaction

from .hospital_members import HospitalMembership


class HospitalProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.OneToOneField(
        "tenants.Client",
        on_delete=models.CASCADE,
        related_name="hospital_profile")

    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="hospital.HospitalMembership",
        related_name="associated_hospitals",
        blank=True
    )

    hospital_code = models.CharField(
        max_length=4,
        unique=True,
        help_text="Unique 3-letter hospital code for PIN generation"
    )

    SUBSCRIPTION_CHOICES = [
        ("trial", "Trial"),
        ("basic", "Basic"),
        ("premium", "Premium"),
    ]
    subscription_plan = models.CharField(max_length=20, choices=SUBSCRIPTION_CHOICES)
    hospital_name = models.CharField(max_length=200, unique=True)
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

        if self.admin_user and not self.admin_user.tenant_memberships.filter(
            tenant=self.tenant,
            role="ADMIN"
        ).exists():
            raise ValidationError("Admin user must have ADMIN role for this hospital")

        if (
            HospitalProfile.objects.filter(license_number=self.license_number)
            .exclude(pk=self.pk)
            .exists()
        ):
            raise ValidationError(
                {"license_number": "This license number is already registered."}
            )
    @transaction.atomic
    def add_staff_member(self, user, role="STAFF"):
        """
        Add a staff member to the hospital profile and ensure tenant association.
        """
        if user.hospital_membership.tenant != self.tenant:
            raise PermissionDenied(
                "User's tenant must match the hospital profile's tenant"
            )

        if hasattr(user, "associated_hospitals") and \
        user.associated_hospitals.exclude(id=self.id).exists():
            raise ValidationError(
                "User is already associated with another hospital"
            )

        # Get or create the tenant permission
        if not user.hospital_memberships.filter(tenant_id=self.tenant.id).exists():
            HospitalMembership.objects.create(
                user=user,
                tenant=self.tenant,
                hospital_profile=self,
                role=role
            )
        user.tenant = self.tenant  # Set default tenant context
        user.save()


    def remove_staff_member(self, user):
        """Remove a staff member from the hospital profile."""
        HospitalMembership = apps.get_model("core", "HospitalMembership")
        HospitalMembership.objects.filter(
            hospital_profile=self,
            user=user
        ).delete()

    def get_staff_by_role(self, role):
        """Get all staff members with a specific role."""
        return self.additional_staff.filter(
            hospitalstaffmembership__role=role
        )

    def get_all_staff(self):
        """
        AReturns all staff members associated with this hospital.

        This includes the admin user and additional staff
        """
        cache_key = f"hospital_{self.id}_members"
        staff = cache.get(cache_key)
        if not staff:
            staff_memberships = self.hospital_memberships.select_related("user").all()
            staff = [{"user": m.user, "role": m.role} for m in staff_memberships]
            cache.set(cache_key, staff, timeout=300)
        return staff


