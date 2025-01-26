
from django.core.validators import RegexValidator
from django.db import models

from .core import PatientBasemodel


class PatientEmergencyContact(PatientBasemodel):
    ADDRESS_TYPES = [
        ("home", "Home"),
        ("work", "Work"),
        ("other", "Other"),
    ]

    address_type = models.CharField(max_length=50, choices=ADDRESS_TYPES, default="home")
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
    relationship = models.CharField(max_length=50, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    phone_primary = models.CharField(
        max_length=20,
        validators=[
            RegexValidator(
                regex=r"^\+?[1-9]\d{1,14}$",
                message="Enter a valid phone number (e.g., +123456789).",
            )
        ],
    )

    is_primary = models.BooleanField(default=False)

    class Meta:
        db_table = "patient_emergency_contacts"  # Specify table name
        indexes = [
            models.Index(fields=["state", "city"]),
            models.Index(fields=["postal_code", "country"]),
            models.Index(fields=["address_type", "is_primary"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["is_primary"],
                condition=models.Q(is_primary=True),
                name="unique_primary_address_per_patient",
            )
        ]

    def __str__(self):
        return f"{self.address_type.capitalize()} Address of {self.patient}"

    def save(self, *args, **kwargs):
        if self.is_primary:
            PatientEmergencyContact.objects.filter(patient=self.patient, is_primary=True).update(
                is_primary=False
            )
        super().save(*args, **kwargs)


