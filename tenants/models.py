from django.db import models
from core.models import MyUser
from django_tenants.models import TenantMixin, DomainMixin

class Client(TenantMixin):
    name = models.CharField(max_length=100)
    paid_until = models.DateField()
    on_trial = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Add status field to track tenant state
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('expired', 'Expired')
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    
    auto_create_schema = True

    def __str__(self):
        return f"{self.name} ({self.schema_name})"

class Domain(DomainMixin):
    tenant = models.ForeignKey(Client, on_delete=models.CASCADE)

    def __str__(self):
        return self.domain
    
    
    
    