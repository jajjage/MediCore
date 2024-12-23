from django.db import models
from core.models import MyUser
from django_tenants.models import TenantMixin, DomainMixin

class Client(TenantMixin):
    name = models.CharField(max_length=100)
    paid_until = models.DateField()
    on_trial = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Auto-create schema for tenant
    auto_create_schema = True
    
    
class Domain(DomainMixin):
    tenant = models.ForeignKey(Client, on_delete=models.CASCADE)
    
    
class HospitalProfile(models.Model):
    tenant = models.OneToOneField(Client, on_delete=models.CASCADE)
    admin_user = models.OneToOneField(MyUser, on_delete=models.CASCADE)
    subscription_plan = models.CharField(
        max_length=20,
        choices=[
            ('trial', 'Trial'),
            ('basic', 'Basic'),
            ('premium', 'Premium')
        ]
    )
    hospital_name = models.CharField(max_length=200)
    license_number = models.CharField(max_length=100)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'hospital_profile'