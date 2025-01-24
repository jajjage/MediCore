import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Department(models.Model):
    """
    Model to represent hospital departments with hierarchy and type classification.

    Supports department staff assignments and sub-department relationships.
    """

    DEPARTMENT_TYPES = [
        ("CLINICAL", "Clinical"),
        ("NURSING", "Nursing"),
        ("DIAGNOSTIC", "Diagnostic"),
        ("ADMINISTRATIVE", "Administrative"),
        ("SUPPORT", "Support"),
        ("AUXILIARY", "Auxiliary")
    ]

    # Primary Fields
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text=_("Unique identifier for the department")
    )
    name = models.CharField(
        max_length=100,
        help_text=_("Name of the department")
    )
    code = models.CharField(
        max_length=20,
        unique=True,
        help_text=_("Unique code for department identification")
    )
    department_type = models.CharField(
        max_length=20,
        choices=DEPARTMENT_TYPES,
        default="CLINICAL",
        help_text=_("Type/category of the department")
    )

    # Hierarchy
    parent_department = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sub_departments",
        help_text=_("Parent department if this is a sub-department")
    )

    min_staff_per_shift = models.IntegerField(default=0)
    emergency_min_staff = models.IntegerField(default=0)
    minimum_staff_required = models.IntegerField(default=0)

    # Department Details
    description = models.TextField(
        null=True,
        blank=True,
        help_text=_("Detailed description of the department")
    )
    location = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text=_("Physical location of the department (Floor/Wing/Building)")
    )
    contact_email = models.EmailField(
        null=True,
        blank=True,
        help_text=_("Contact email for the department")
    )
    contact_phone = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text=_("Contact phone number for the department")
    )

    # Department Head
    department_head = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="headed_departments",
        help_text=_("User assigned as head of this department")
    )

    # Status and Meta
    is_active = models.BooleanField(
        default=True,
        help_text=_("Whether the department is currently active")
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        null=True,
        help_text=_("Timestamp when the department was created")
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        null=True,
        help_text=_("Timestamp when the department was last updated")
    )

    class Meta:
        db_table = "department"
        unique_together = ["code", "name"]
        indexes = [
            models.Index(fields=["name",  "is_active"]),
            models.Index(fields=["department_head"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(name__isnull=False),
                name="department_name_not_null"
            )
        ]
        ordering = ["name"]
        verbose_name = _("Department")
        verbose_name_plural = _("Departments")

    def __str__(self):
        return f"{self.name} ({self.code})"

    # def clean(self):
    #     """Validate department data."""
    #     # Only validate if both fields are set
    #     if self.parent_department and self.hospital and self.parent_department.hospital != self.hospital:
    #         raise ValidationError({
    #             "parent_department": _("Parent department must belong to the same hospital")
    #         })

    def save(self, *args, **kwargs):
        skip_validation = kwargs.pop("skip_validation", False)
        if not skip_validation:
            self.full_clean()
        super().save(*args, **kwargs)


    def get_staff_count(self):
        """Return total staff in department."""
        return self.department_members.count()

    def get_active_staff(self):
        """Return only active staff."""
        return self.department_members.filter(is_active=True)

    def get_sub_departments(self):
        """Return all sub-departments."""
        return self.sub_departments.all()

    @property
    def is_clinical(self):
        """Check if department is clinical type."""
        return self.department_type == "CLINICAL"

    @property
    def full_hierarchy_name(self):
        """Return full department name including parent."""
        if self.parent_department:
            return f"{self.parent_department.name} - {self.name}"
        return self.name


