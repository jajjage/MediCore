import uuid

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.utils.translation import gettext_lazy as _

from .departments import Department
from .staff_transfer import StaffTransfer


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

    assignment_type = models.CharField(
        max_length=20,
        choices=[
            ("PERMANENT", "Permanent Assignment"),
            ("TEMPORARY", "Temporary Assignment"),
            ("ROTATION", "Rotation"),
            ("ON_CALL", "On-Call Coverage"),
            ("TRAINING", "Training Period")
        ],
        default="PERMANENT"
    )

    time_allocation = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Percentage of time allocated to this department",
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

    schedule_pattern = models.JSONField(
        default=dict,
        help_text="Weekly/monthly schedule pattern"
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

    max_weekly_hours = models.IntegerField(default=40)
    rest_period_hours = models.IntegerField(default=12)
    emergency_contact = models.CharField(max_length=100)
    is_emergency_response = models.BooleanField(default=False)
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
    def assign_schedule(self, schedule_data, start_date, end_date):
        """
        Assign working schedule for the staff member.
        """
        self.schedule_pattern = {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "pattern": schedule_data
        }
        self.save()

    def initiate_transfer(self, to_department, transfer_type, effective_date, **kwargs):
        with transaction.atomic():
            # Create new department assignment
            new_assignment = DepartmentMember.objects.create(
                user=self.user,
                department=to_department,
                role=self.role,
                start_date=effective_date,
                assignment_type="TRANSFER",
                time_allocation=kwargs.get("time_allocation", 100)
            )

            # Create transfer record
            transfer = StaffTransfer.objects.create(
                from_assignment=self,
                to_assignment=new_assignment,
                transfer_type=transfer_type,
                effective_date=effective_date,
                **kwargs
            )

            # Handle primary department changes
            if self.is_primary:
                self.is_primary = False
                new_assignment.is_primary = True

            # Update end date for current assignment
            self.end_date = effective_date
            self.is_active = False
            self.save()

            return transfer

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
