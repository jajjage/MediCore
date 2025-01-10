import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from .departments import Department


class DepartmentMember(models.Model):
    """
    Model to represent staff assignments to departments.

    Supports multiple roles and departments per staff member.
    """

    ROLE_TYPES = [
        ("HEAD", "Department Head"),
        ("DOCTOR", "Doctor"),
        ("NURSE", "Nurse"),
        ("TECHNICIAN", "Technician"),
        ("STAFF", "Staff Member"),
        ("ADMIN", "Administrative Staff")
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name="staff_members",
        help_text=_("Department the staff member belongs to")
    )
    user = models.ForeignKey(
        "staff.StaffMember",
        on_delete=models.CASCADE,
        related_name="department_memberships",
        help_text=_("User assigned to the department")
    )
    role = models.CharField(
        max_length=30,
        choices=ROLE_TYPES,
        help_text=_("Role of the staff member in the department")
    )
    # Assignment Details
    start_date = models.DateField(
        help_text=_("Date when the staff member started in this department")
    )
    end_date = models.DateField(
        null=True,
        blank=True,
        help_text=_("Date when the staff member ended their role (if applicable)")
    )
    is_primary = models.BooleanField(
        default=False,
        help_text=_("Whether this is the staff member's primary department")
    )

    # Meta
    created_at = models.DateTimeField(
        auto_now_add=True,
        null=True,
        help_text=_("Timestamp when the assignment was created")
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        null=True,
        help_text=_("Timestamp when the assignment was last updated")
    )
    is_active = models.BooleanField(
        default=True,
        help_text=_("Whether the assignment is currently active")
    )

    class Meta:
        db_table = "department_member"
        unique_together = ["department", "user", "role"]
        indexes = [
            models.Index(fields=["user", "department", "is_active"]),
            models.Index(fields=["role", "is_active"]),
            models.Index(fields=["start_date", "end_date"]),
        ]
        ordering = ["-start_date"]
        verbose_name = _("Department Member")
        verbose_name_plural = _("Department Members")

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.department.name} ({self.get_role_display()})"

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        # Validate dates
        if self.end_date and self.end_date <= self.start_date:
            raise ValidationError({
                "end_date": "End date must be after start date"
            })

        # Validate same hospital
        if self.user_id and self.department_id:  # Check if both fields are set
            user_hospital = self.user.hospital_id
            department_hospital = self.department.hospital_id

            if user_hospital != department_hospital:
                raise ValidationError({
                    "user": "User must belong to the same hospital as the department",
                    "department": "Department must belong to the same hospital as the user"
                })

    @classmethod
    def from_db(cls, db, field_names, values):
        instance = super().from_db(db, field_names, values)
        # Store original values to check in clean()
        instance._loaded_values = dict(zip(field_names, values))
        return instance

    def get_role_history(self):
        """Get all roles user has had in this department."""
        return DepartmentMember.objects.filter(
            user=self.user,
            department=self.department
        ).order_by("-start_date")
