import uuid

from django.db import models

from .hospital_members import HospitalMembership


class Role(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50, unique=True)  # E.g., Doctor, Nurse, etc.
    description = models.TextField(blank=True, null=True)
    code = models.CharField(max_length=50, unique=True)
    permissions = models.ManyToManyField("auth.Permission", blank=True)
    groups = models.ManyToManyField("auth.Group", blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "hospital_role"
        indexes = [
            models.Index(fields=["name", "is_active"]),
            models.Index(fields=["code" ]),
        ]

    def __str__(self):
        return self.name

    def get_staff_count(self, tenant):
        """Get count of staff with this role."""
        return HospitalMembership.objects.filter(role=self.code, is_active=True, tenant_id=tenant.id).count()
