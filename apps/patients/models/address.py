
from django.core.validators import RegexValidator
from django.db import models

from .core import Basemodel


class PatientAddress(Basemodel):
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
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "patient_addresses"
        indexes = [
            models.Index(fields=["postal_code"]),
            models.Index(fields=["state"]),
            models.Index(fields=["city"]),
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
        if self.is_primary:
            PatientAddress.objects.filter(patient=self.patient, is_primary=True).update(
                is_primary=False
            )
        super().save(*args, **kwargs)
