import uuid
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.db.models import Q, Sum
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.staff.utils.exceptions import BusinessLogicError

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
        related_name="department_members",
        help_text=_("Department the staff member belongs to")
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="department_members",
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
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))]
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
            models.Index(fields=["start_date", "end_date", "time_allocation"]),
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
        if not hasattr(self, "_loaded_values"):
            print("the else")
            return
        print("clean get called")
        self._validate_dates()
        self._validate_role_changes()
        self._validate_workload()
        self._validate_overlapping_assignments()


    def _validate_overlapping_assignments(self):
        print("_validate_overlapping_assignments")
        if self.is_active:
            active_assignments = DepartmentMember.objects.filter(
                user=self.user,
                is_active=True
            )
            if self.pk:
                active_assignments = active_assignments.exclude(pk=self.pk)
            if active_assignments.exists():
                raise ValidationError(
                    _("Staff member already has an active department assignment")
                )

    def _validate_dates(self):
        print("_validate_dates")
        if self.end_date and self.end_date <= self.start_date:
            raise ValidationError({
                "end_date": "End date must be after start date"
            })

        # Validate against existing assignments
        overlapping = DepartmentMember.objects.filter(
            user=self.user,
            department=self.department,
            role=self.role
        ).exclude(pk=self.pk).filter(
            Q(start_date__lte=self.start_date, end_date__gte=self.start_date) |
            Q(start_date__lte=self.end_date, end_date__gte=self.end_date) if self.end_date else Q()
        )

        if overlapping.exists():
            raise ValidationError("Overlapping assignment period detected")

    def _validate_role_changes(self):
        print(dir(self))
        if not self.pk:
            return
        if self.role:
            active_role = DepartmentMember.objects.filter(
                    user=self.user,
                    is_active=True
                )
            if self.pk:
                active_role = active_role.exclude(pk=self.pk)
                old_role = active_role.role
                print(f"_validate_role_changes {old_role}")
                if old_role and old_role != self.role:
                    # Check if role change is allowed
                    if self.transfer_in_progress(): #This need to be created
                        raise ValidationError("Cannot change role during transfer")

                    # Validate department head changes
                    if old_role == "HEAD" or self.role == "HEAD":
                        self._validate_head_role_change()

    def _validate_head_role_change(self):
        print("_validate_head_role_change")
        if self.role == "HEAD":
            existing_head = DepartmentMember.objects.filter(
                department=self.department,
                role="HEAD",
                is_active=True
            ).exclude(pk=self.pk).exists()

            if existing_head:
                raise ValidationError("Department already has an active head")

    def _validate_workload(self):
        print("_validate_workload")
        if not self.is_active:
            return

        # Calculate total time allocation
        total_allocation = DepartmentMember.objects.filter(
            user=self.user,
            is_active=True
        ).exclude(pk=self.pk).aggregate(
            total=Sum("time_allocation")
        )["total"] or 0

        if (total_allocation + self.time_allocation) > 100:  # noqa: PLR2004
            raise ValidationError({
                "time_allocation": f"Total time allocation would exceed 100% ({total_allocation + self.time_allocation}%)"
            })

    def initiate_transfer(self, to_department, transfer_type, effective_date, **kwargs):
        """Enhanced transfer initiation with additional checks and workflows."""
        with transaction.atomic():
            # Validate minimum staffing levels
            self._validate_staffing_levels(effective_date)

            # Validate transfer eligibility
            # self._validate_transfer_eligibility(to_department, effective_date)

            # Create new assignment with proper attribute inheritance
            new_assignment = DepartmentMember.objects.create(
                user=self.user,
                department=to_department,
                role=kwargs.get("new_role", self.role),
                start_date=effective_date,
                assignment_type="TRANSFER",
                time_allocation=kwargs.get("time_allocation", self.time_allocation),
                max_weekly_hours=kwargs.get("max_weekly_hours", self.max_weekly_hours),
                rest_period_hours=self.rest_period_hours,
                is_emergency_response=self.is_emergency_response,
                is_primary=self.is_primary
                #Shift need to be created
            )

            # Create transfer record with enhanced tracking
            transfer = StaffTransfer.objects.create(
                from_assignment=self,
                to_assignment=new_assignment,
                transfer_type=transfer_type,
                effective_date=effective_date,
                notice_period=kwargs.get("notice_period", 30),
                required_documents=kwargs.get("required_documents", []),
                handover_checklist=self._generate_handover_checklist(to_department),
                approved_by = None,
                **kwargs
            )

            # Update current assignment
            if self.is_primary:
                self.is_primary = False
                new_assignment.is_primary = True

            self.save()

            return transfer

    def _validate_staffing_levels(self, effective_date):
        """Validate department staffing levels post-transfer."""
        department = self.department
        future_staff_count = department.get_active_staff().filter(
            Q(end_date__isnull=True) |
            Q(end_date__gt=effective_date)
        ).count()

        if future_staff_count < department.minimum_staff_required:
            raise ValidationError(
                f"Transfer would violate minimum staffing requirement "
                f"({future_staff_count} vs {department.minimum_staff_required} required)"
            )

    def _generate_handover_checklist(self, to_department):
        """Generate role-specific handover checklist."""
        base_checklist = {
            "equipment_returned": False,
            "access_cards_updated": False,
            "system_access_updated": False,
            "documents_transferred": False,
        }

        role_specific = {
            "HEAD": {
                "leadership_handover": False,
                "department_reports": False,
                "ongoing_projects": False,
            },
            "DOCTOR": {
                "patient_handover": False,
                "prescriptions_review": False,
            },
            "NURSE": {
                "patient_care_notes": False,
                "medication_schedules": False,
            }
        }

        checklist = base_checklist.copy()
        checklist.update(role_specific.get(self.role, {}))
        return checklist


    @property
    def requires_immediate_replacement(self):
        """Check if role requires immediate replacement."""
        return self.role in ["HEAD", "DOCTOR"] and self.is_primary

    def get_coverage_requirements(self):
        """Get coverage requirements based on role and assignment type."""
        return {
            "immediate_replacement_needed": self.requires_immediate_replacement,
            "minimum_notice_period": self.notice_period,
            "special_requirements": self._get_special_requirements(),
        }

    def check_staffing_requirements(self):
        """
        Check if ending this assignment would violate staffing requirements.
        """
        requires_replacement = self.role in ["HEAD", "DOCTOR"] and self.is_primary
        future_staff_count = self.department.get_active_staff().filter(
            end_date__gt=timezone.now().date()
        ).count()

        return {
            "requires_replacement": requires_replacement,
            "does_minimum_staff_met": future_staff_count >= self.department.minimum_staff_required,
            "current_staff_count": future_staff_count,
            "minimum_required": self.department.minimum_staff_required
        }

    def _get_special_requirements(self):
        requirements = []
        if self.is_emergency_response:
            requirements.append("Emergency response capability required")
        if self.role == "HEAD":
            requirements.append("Leadership experience required")
        return requirements

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

    @classmethod
    def get_staff_workload(cls, staff_member, date=None):
        """Get detailed workload analysis for a staff member."""
        assignments = cls.objects.filter(
            user=staff_member,
            is_active=True
        ).select_related("department")

        return {
            "total_allocation": sum(a.time_allocation for a in assignments),
            "departments": [
                {
                    "department": a.department.name,
                    "role": a.get_role_display(),
                    "allocation": a.time_allocation,
                    # "schedule": a.schedule_pattern, we need to fecth the user generated shift
                } for a in assignments
            ],
            "weekly_hours": sum(a.max_weekly_hours for a in assignments)
        }

    def deactivate(self):
        """Deactivate this assignment."""
        self.is_active = False
        self.end_date = timezone.now()
        self.save()

    def reactivate(self):
        """Reactivate this assignment."""
        self.clean()  # This will raise an error if user has another active assignment
        self.is_active = True
        self.end_date = None
        self.save()

    def end_assignment(self, end_date, reason=None):
        """
        End this department member's assignment.
        """
        if self.end_date and self.end_date <= timezone.now().date():
            raise BusinessLogicError("Assignment already ended", "ALREADY_ENDED")

        if end_date < timezone.now().date():
            raise BusinessLogicError("End date cannot be in the past", "INVALID_END_DATE")

        self.end_date = end_date
        self.is_active = False
        self.full_clean()
        self.save()

    def get_schedule_pattern(self, user_id):
        """Get the schedule pattern for this assignment."""
        if not isinstance(user_id, (str, uuid.UUID)):
            raise TypeError("user_id must be a string or UUID")

        if str(self.user.id) != str(user_id):
            raise ValidationError("Schedule can only be accessed by assigned user")

        return self.schedule_pattern
