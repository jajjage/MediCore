from django.db import models
from django.contrib.auth import get_user_model
from tenants.models import Client

# Create your models here.
User = get_user_model()

class HospitalProfile(models.Model):
    tenant = models.OneToOneField(Client, on_delete=models.CASCADE)
    admin_user = models.OneToOneField(User, on_delete=models.CASCADE)
    
    SUBSCRIPTION_CHOICES = [
        ('trial', 'Trial'),
        ('basic', 'Basic'),
        ('premium', 'Premium')
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
        db_table = 'hospital_profile'

    def __str__(self):
        return self.hospital_name