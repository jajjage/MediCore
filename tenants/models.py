import uuid

from django.db import models
from django_tenants.models import DomainMixin, TenantMixin


class Client(TenantMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    paid_until = models.DateField()
    on_trial = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Add status field to track tenant state
    STATUS_CHOICES = [
        ("active", "Active"),
        ("suspended", "Suspended"),
        ("expired", "Expired"),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="active")

    auto_create_schema = True

    def __str__(self):
        return f"{self.name} ({self.schema_name})"


class Domain(DomainMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="domains")

    def __str__(self):
        return self.domain
