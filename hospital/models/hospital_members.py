import uuid
from datetime import timezone

from django.conf import settings
from django.db import models

from .soft_delete import SoftDeleteModel


class HospitalMembership(SoftDeleteModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="hospital_memberships_user"
    )
    tenant = models.ForeignKey(
        "tenants.Client",
        on_delete=models.CASCADE,
        related_name="hospital_memberships_tenant")

    hospital_profile = models.ForeignKey(
        "hospital.HospitalProfile",
        on_delete=models.CASCADE,
        related_name="hospital_memberships_profile",
        null=True)

    role = models.ForeignKey(
        "hospital.Role",
        on_delete=models.PROTECT,
        related_name="hospital_memberships_role",
        default=None,
        null=True
        )
    is_tenant_admin = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "hospital_memberships"
        unique_together = [
            ("user", "hospital_profile", "tenant"),
            ("user", "tenant", "role")  # Prevent duplicate roles in same tenant]
        ]
        indexes = [
            models.Index(fields=["tenant", "role", "is_deleted"]),
            models.Index(fields=["user", "hospital_profile", "is_tenant_admin"]),
            models.Index(fields=["created_at", "is_deleted"]),
        ]

        permissions = [
        ("generate_patient_pin", "Can generate patient PINs")

        ]

    def delete(self, hard_delete=None):
        if hard_delete is True:
            return super().hard_delete()
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()
        return None
