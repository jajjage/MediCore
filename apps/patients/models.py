import uuid

from django.core.validators import RegexValidator
from django.db import connection, models
from simple_history.models import HistoricalRecords

from utils.encryption import field_encryption


class Patient(models.Model):
    MAX_PIN_LENGTH = 15

    GENDER_CHOICES = [
        ("M", "Male"),
        ("F", "Female"),
        ("O", "Other"),
    ]

    # Core details
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pin = models.CharField(
        max_length=MAX_PIN_LENGTH, unique=True, editable=False, db_index=True
    )
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    nin_encrypted = models.CharField(max_length=255, blank=True, null=True)
    history = HistoricalRecords(user_model="staff.StaffMember")
    # Contact details
    email = models.EmailField(unique=True)
    phone_primary = models.CharField(
        max_length=20,
        validators=[
            RegexValidator(
                regex=r"^\+?[1-9]\d{1,14}$",
                message="Enter a valid phone number (e.g., +123456789).",
            )
        ],
    )

    # Patient status
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "patients"
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["last_name", "first_name"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=["email"], name="unique_email"),
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


class PatientEmergencyContact(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.OneToOneField(
        Patient, on_delete=models.CASCADE, related_name="emergency_contact"
    )
    name = models.CharField(max_length=100, blank=True, null=True)
    history = HistoricalRecords(user_model="staff.StaffMember")
    phone = models.CharField(max_length=20, blank=True, null=True)
    relationship = models.CharField(max_length=50, blank=True, null=True)


class PatientAllergy(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(
        Patient, on_delete=models.CASCADE, related_name="allergies"
    )
    name = models.CharField(max_length=100)
    history = HistoricalRecords(user_model="staff.StaffMember")
    severity = models.CharField(
        max_length=50,
        choices=[("Mild", "Mild"), ("Moderate", "Moderate"), ("Severe", "Severe")],
    )
    reaction = models.TextField(blank=True, null=True)


class PatientChronicCondition(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(
        Patient, on_delete=models.CASCADE, related_name="chronic_conditions"
    )
    condition = models.CharField(max_length=100)
    history = HistoricalRecords(user_model="staff.StaffMember")
    diagnosis_date = models.DateField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)


class PatientDemographics(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.OneToOneField(
        Patient, on_delete=models.CASCADE, related_name="demographics"
    )
    history = HistoricalRecords(user_model="staff.StaffMember")
    blood_type = models.CharField(max_length=5, blank=True, null=True)
    height_cm = models.DecimalField(
        max_digits=5, decimal_places=2, blank=True, null=True
    )
    weight_kg = models.DecimalField(
        max_digits=5, decimal_places=2, blank=True, null=True
    )
    gender = models.CharField(max_length=50, blank=True, null=True)
    race = models.CharField(max_length=50, blank=True, null=True)
    ethnicity = models.CharField(max_length=50, blank=True, null=True)
    preferred_language = models.CharField(max_length=50, blank=True, null=True)
    marital_status = models.CharField(max_length=50, blank=True, null=True)
    employment_status = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "patient_demographics"

        permissions = [
            ("view_patient", "Can view patient"),
            ("view_patient_demographics", "Can view patient demographics"),
        ]


class PatientAddress(models.Model):
    ADDRESS_TYPES = [
        ("home", "Home"),
        ("work", "Work"),
        ("other", "Other"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(
        "Patient", on_delete=models.CASCADE, related_name="addresses"
    )
    address_type = models.CharField(
        max_length=50, choices=ADDRESS_TYPES, default="home"
    )
    history = HistoricalRecords(user_model="staff.StaffMember")
    street_address1 = models.CharField(max_length=255)
    street_address2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(
        max_length=20,
        validators=[
            RegexValidator(
                regex=r"^\d{5}(-\d{4})?$",
                message="Enter a valid postal code (e.g., 12345 or 12345-6789).",
            )
        ],
    )
    country = models.CharField(max_length=100, default="United States")
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "patient_addresses"
        indexes = [
            models.Index(fields=["postal_code"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["patient", "is_primary"],
                condition=models.Q(is_primary=True),
                name="unique_primary_address_per_patient",
            )
        ]
        permissions = [
            ("view_patient", "Can view patient"),
            ("view_patient_address", "Can view patient address"),
        ]

    def __str__(self):
        return f"{self.address_type.capitalize()} Address of {self.patient}"

    def save(self, *args, **kwargs):
        # Enforce only one primary address per patient
        if self.is_primary:
            PatientAddress.objects.filter(patient=self.patient, is_primary=True).update(
                is_primary=False
            )
        super().save(*args, **kwargs)


class PatientMedicalReport(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(
        Patient, on_delete=models.CASCADE, related_name="medical_reports"
    )
    title = models.CharField(
        max_length=255, blank=True, null=True
    )  # E.g., "Diagnosis", "Follow-Up Notes"
    history = HistoricalRecords(user_model="staff.StaffMember")
    description = models.TextField()  # The doctor's notes or observations
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} for {self.patient.first_name} {self.patient.last_name}"
