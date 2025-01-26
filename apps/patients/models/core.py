import uuid

from django.conf import settings
from django.db import connection, models
from django.db.models import Q
from django.utils.timezone import now
from simple_history.models import HistoricalRecords

from utils.encryption import field_encryption

from .dynamic_related_name import BaseModelMeta


class PatientBasemodel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    history = HistoricalRecords(inherit=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        abstract = True

class Patient(models.Model):
    MAX_PIN_LENGTH = 15

    # Core details
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, related_name="patient_profile")
    pin = models.CharField(max_length=MAX_PIN_LENGTH, unique=True, editable=False, db_index=True)
    date_of_birth = models.DateField(blank=True, null=True)
    nin_encrypted = models.CharField(max_length=255, blank=True, null=True)
    demographics = models.OneToOneField("PatientDemographics", null=True, on_delete=models.CASCADE, related_name="patient_profile")
    emergency_contact = models.OneToOneField("PatientEmergencyContact", null=True, on_delete=models.CASCADE, related_name="patient_profile")
    history = HistoricalRecords()

    # Patient status
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "patients"
        indexes = [
            models.Index(fields=["date_of_birth", "is_active"]),
            models.Index(fields=["pin"]),
            models.Index(fields=["nin_encrypted"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=["pin"], name="unique_pin"),
        ]

    @property
    def nin_number(self):
        if self.nin_encrypted:
            return field_encryption.decrypt(self.nin_encrypted)
        return None

    @nin_number.setter
    def nin_number(self, value):
        if value:
            self.nin_encrypted = field_encryption.encrypt(value)
        else:
            self.nin_encrypted = None

    def generate_pin(self, hospital_code):
        """Generate PIN without requiring request object."""
        if not self.pin:
            with connection.cursor() as cursor:
                cursor.execute("SELECT nextval('patient_pin_seq_middle')")
                middle_val = cursor.fetchone()[0]
                cursor.execute("SELECT nextval('patient_pin_seq_last')")
                last_val = cursor.fetchone()[0]

            self.pin = f"{hospital_code}-{middle_val:04d}-{last_val:04d}"
            self.save(update_fields=["pin"])
        return self.pin

    def calculate_age(self):
        today = now().date()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )

    @classmethod
    def search(cls, query):
        return cls.objects.filter(
            Q(pin__icontains=query)
            | Q(user__first_name__icontains=query)
            | Q(user__last_name__icontains=query)
            | Q(email__icontains=query)
            | Q(phone_primary__icontains=query)
        ).select_related("demographics")
