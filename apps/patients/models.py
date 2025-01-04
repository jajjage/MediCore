import secrets
import uuid

from django.db import models, transaction

from utils.encryption import encrypt_sensitive_fields, field_encryption


class Patient(models.Model):

    GENDER_CHOICES = [
        ("M", "Male"),
        ("F", "Female"),
        ("O", "Other"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pin = models.CharField(max_length=15, unique=True, editable=False, db_index=True)  # Unique Identifier
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    nin = models.CharField(max_length=255, help_text="Encrypted NIN", blank=True, null=True)
    email = models.EmailField(unique=True)
    phone_primary = models.CharField(max_length=20)
    phone_secondary = models.CharField(max_length=20, blank=True, null=True)
    preferred_language = models.CharField(max_length=50, default="en")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    nin_encrypted = models.CharField(max_length=255, blank=True, null=True)
    class Meta:
        db_table = "patients"
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["last_name", "first_name"]),
        ]

    @encrypt_sensitive_fields(["ssn"])
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    @property
    def nin_number(self):
        if self.nin_encrypted:
            return field_encryption.decrypt(self.nin_encrypted)
        return None

    @nin_number.setter
    def ssn(self, value):
        if value:
            self.nin_encrypted = field_encryption.encrypt(value)
        else:
            self.nin_encrypted = None

    def generate_pin(self, request):
        """Generate a unique PIN for the patient using hospital code and random digits.

        Format: XXXXX-NNNNNN (where X is hospital code and N is number).
        """
        if not self.pin:
            with transaction.atomic():
                # Get the host and extract relevant parts for the hospital code
                host = request.get_host().split(":")[0]
                subdomain = host.split(".")[0]
                # Make sure hospital code is exactly 5 characters
                hospital_code = f"{subdomain[:3].upper()}{subdomain[-2:].upper()}"[:5]
                hospital_code = hospital_code.ljust(5, "X")  # Pad with X if too short

                # Generate a 6-digit PIN
                max_attempts = 10
                attempts = 0

                while attempts < max_attempts:
                    pin_numbers = "".join(str(secrets.randbelow(10)) for _ in range(6))
                    complete_pin = f"{hospital_code}-{pin_numbers}"

                    # Check if this PIN is unique
                    if not Patient.objects.filter(pin=complete_pin).exists():
                        self.pin = complete_pin
                        self.save()
                        return complete_pin

                    attempts += 1
                raise ValueError("Failed to generate a unique PIN after maximum attempts")
        return self.pin


class PatientDemographics(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.OneToOneField(
        Patient, on_delete=models.CASCADE, related_name="demographics"
    )
    blood_type = models.CharField(max_length=5, blank=True, null=True)
    height_cm = models.DecimalField(
        max_digits=5, decimal_places=2, blank=True, null=True
    )
    weight_kg = models.DecimalField(
        max_digits=5, decimal_places=2, blank=True, null=True
    )
    allergies = models.JSONField(default=list, blank=True, null=True)
    gender = models.CharField(max_length=50, blank=True, null=True)
    race = models.CharField(max_length=50, blank=True, null=True)
    ethnicity = models.CharField(max_length=50, blank=True, null=True)
    preferred_language = models.CharField(max_length=50, blank=True, null=True)
    marital_status = models.CharField(max_length=50, blank=True, null=True)
    employment_status = models.CharField(max_length=50, blank=True, null=True)
    emergency_contact_name = models.CharField(max_length=100, blank=True, null=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True, null=True)
    chronic_conditions = models.JSONField(default=list, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "patient_demographics"

        permissions = [
            ("view_patient", "Can view patient"),
            ("view_patient_demographics", "Can view patient demographics"),
        ]


class PatientAddress(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(
        Patient, on_delete=models.CASCADE, related_name="addresses"
    )
    address_type = models.CharField(max_length=50)  # home, work, etc.
    street_address1 = models.CharField(max_length=255)
    street_address2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100, default="United States")
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "patient_addresses"
        indexes = [
            models.Index(fields=["postal_code"]),
        ]

        permissions = [
            ("view_patient", "Can view patient"),
            ("view_patient_address", "Can view patient address"),
        ]
class PatientMedicalReport(models.Model):
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="reports"
    )
    title = models.CharField(max_length=255)  # E.g., "Diagnosis", "Follow-Up Notes"
    description = models.TextField()  # The doctor's notes or observations
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} for {self.patient.first_name} {self.patient.last_name}"
