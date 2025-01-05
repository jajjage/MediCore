import uuid

from django.core.validators import RegexValidator
from django.db import connection, models
from django.db.models import Q
from django.utils.timezone import now
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
    pin = models.CharField(max_length=MAX_PIN_LENGTH, unique=True, editable=False, db_index=True)
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
            models.Index(fields=["date_of_birth"]),
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
        if not self.pin:
            host = request.get_host().split(":")[0]
            subdomain = host.split(".")[0]
            hospital_code = subdomain[:3].upper()

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
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(email__icontains=query)
            | Q(phone_primary__icontains=query)
        ).select_related("demographics")
