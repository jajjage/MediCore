import uuid
from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from core.models import MyUser
from tenants.models import Client

# Create your models here.
User = get_user_model()


class HospitalProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.OneToOneField(Client, on_delete=models.CASCADE)
    admin_user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

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
        # Add validation
        if self.tenant_id and self.pk is None:  # New hospital
            if Client.objects.filter(schema_name=self.tenant.schema_name).exists():
                raise ValidationError({"tenant": "A tenant with this schema name already exists."})

        if MyUser.objects.filter(email=self.contact_email).exists():
            raise ValidationError({"contact_email": "A user with this email already exists."})

        if HospitalProfile.objects.filter(license_number=self.license_number).exclude(pk=self.pk).exists():
            raise ValidationError({"license_number": "This license number is already registered."})
