
import uuid

from django.db import connection, models

from utils.encryption import encrypt_sensitive_fields, field_encryption


class Patient(models.Model):
    MAX_PIN_LENGTH = 15

    GENDER_CHOICES = [
        ("M", "Male"),
        ("F", "Female"),
        ("O", "Other"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pin = models.CharField(max_length=20, unique=True, editable=False, db_index=True)  # Unique Identifier
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
            # Get hospital code
            host = request.get_host().split(":")[0]
            subdomain = host.split(".")[0]
            hospital_code = subdomain[:3].upper()

            # Get next sequence value
            with connection.cursor() as cursor:
                cursor.execute("SELECT nextval('patient_pin_seq_middle')")
                middle_val = cursor.fetchone()[0]

                cursor.execute("SELECT nextval('patient_pin_seq_last')")
                last_val = cursor.fetchone()[0]

            # Format PIN with the new structure
            self.pin = f"{hospital_code}-{middle_val:04d}-{last_val:04d}"
            self.save(update_fields=["pin"])

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
    title = models.CharField(max_length=255, blank=True,   null=True)  # E.g., "Diagnosis", "Follow-Up Notes"
    description = models.TextField()  # The doctor's notes or observations
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} for {self.patient.first_name} {self.patient.last_name}"
