# Generated by Django 5.1.4 on 2025-01-25 14:27

import apps.staff.utils.validators
import django.core.validators
import django.db.models.deletion
import uuid
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Department",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        help_text="Unique identifier for the department",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        help_text="Name of the department", max_length=100
                    ),
                ),
                (
                    "code",
                    models.CharField(
                        help_text="Unique code for department identification",
                        max_length=20,
                        unique=True,
                    ),
                ),
                (
                    "department_type",
                    models.CharField(
                        choices=[
                            ("CLINICAL", "Clinical"),
                            ("NURSING", "Nursing"),
                            ("DIAGNOSTIC", "Diagnostic"),
                            ("ADMINISTRATIVE", "Administrative"),
                            ("SUPPORT", "Support"),
                            ("AUXILIARY", "Auxiliary"),
                        ],
                        default="CLINICAL",
                        help_text="Type/category of the department",
                        max_length=20,
                    ),
                ),
                ("min_staff_per_shift", models.IntegerField(default=0)),
                ("emergency_min_staff", models.IntegerField(default=0)),
                ("minimum_staff_required", models.IntegerField(default=0)),
                (
                    "description",
                    models.TextField(
                        blank=True,
                        help_text="Detailed description of the department",
                        null=True,
                    ),
                ),
                (
                    "location",
                    models.CharField(
                        blank=True,
                        help_text="Physical location of the department (Floor/Wing/Building)",
                        max_length=100,
                        null=True,
                    ),
                ),
                (
                    "contact_email",
                    models.EmailField(
                        blank=True,
                        help_text="Contact email for the department",
                        max_length=254,
                        null=True,
                    ),
                ),
                (
                    "contact_phone",
                    models.CharField(
                        blank=True,
                        help_text="Contact phone number for the department",
                        max_length=20,
                        null=True,
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        default=True,
                        help_text="Whether the department is currently active",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        help_text="Timestamp when the department was created",
                        null=True,
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        help_text="Timestamp when the department was last updated",
                        null=True,
                    ),
                ),
                (
                    "department_head",
                    models.ForeignKey(
                        blank=True,
                        help_text="User assigned as head of this department",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="headed_departments",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "parent_department",
                    models.ForeignKey(
                        blank=True,
                        help_text="Parent department if this is a sub-department",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="sub_departments",
                        to="staff.department",
                    ),
                ),
            ],
            options={
                "verbose_name": "Department",
                "verbose_name_plural": "Departments",
                "db_table": "department",
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="DepartmentMember",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "role",
                    models.CharField(
                        choices=[
                            ("HEAD", "Department Head"),
                            ("DOCTOR", "Doctor"),
                            ("NURSE", "Nurse"),
                            ("TECHNICIAN", "Technician"),
                            ("STAFF", "Staff Member"),
                            ("ADMIN", "Administrative Staff"),
                        ],
                        help_text="Role of the staff member in the department",
                        max_length=30,
                    ),
                ),
                (
                    "start_date",
                    models.DateField(
                        help_text="Date when the staff member started in this department"
                    ),
                ),
                (
                    "end_date",
                    models.DateField(
                        blank=True,
                        help_text="Date when the staff member ended their role (if applicable)",
                        null=True,
                    ),
                ),
                (
                    "is_primary",
                    models.BooleanField(
                        default=False,
                        help_text="Whether this is the staff member's primary department",
                    ),
                ),
                (
                    "assignment_type",
                    models.CharField(
                        choices=[
                            ("PERMANENT", "Permanent Assignment"),
                            ("TEMPORARY", "Temporary Assignment"),
                            ("ROTATION", "Rotation"),
                            ("ON_CALL", "On-Call Coverage"),
                            ("TRAINING", "Training Period"),
                        ],
                        default="PERMANENT",
                        max_length=20,
                    ),
                ),
                (
                    "time_allocation",
                    models.DecimalField(
                        decimal_places=2,
                        help_text="Percentage of time allocated to this department",
                        max_digits=5,
                        validators=[
                            django.core.validators.MinValueValidator(Decimal("0")),
                            django.core.validators.MaxValueValidator(Decimal("100")),
                        ],
                    ),
                ),
                (
                    "schedule_pattern",
                    models.JSONField(
                        default=dict,
                        help_text="Weekly/monthly schedule pattern",
                        validators=[
                            apps.staff.utils.validators.validate_schedule_pattern
                        ],
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        help_text="Timestamp when the assignment was created",
                        null=True,
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        help_text="Timestamp when the assignment was last updated",
                        null=True,
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        default=True,
                        help_text="Whether the assignment is currently active",
                    ),
                ),
                ("max_weekly_hours", models.IntegerField(default=40)),
                ("rest_period_hours", models.IntegerField(default=12)),
                ("emergency_contact", models.CharField(max_length=100)),
                ("is_emergency_response", models.BooleanField(default=False)),
                (
                    "department",
                    models.ForeignKey(
                        help_text="Department the staff member belongs to",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="department_members",
                        to="staff.department",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        help_text="User assigned to the department",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="department_members",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Department Member",
                "verbose_name_plural": "Department Members",
                "db_table": "department_member",
                "ordering": ["-start_date"],
            },
        ),
        migrations.CreateModel(
            name="DoctorProfile",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("qualification", models.CharField(max_length=255)),
                ("years_of_experience", models.PositiveIntegerField()),
                ("certification_number", models.CharField(blank=True, max_length=100)),
                ("specialty_notes", models.TextField(blank=True)),
                ("specialization", models.CharField(max_length=100)),
                ("license_number", models.CharField(max_length=50, unique=True)),
                (
                    "availability",
                    models.JSONField(
                        default=dict, help_text="Weekly schedule in JSON format"
                    ),
                ),
                (
                    "consulting_fee",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=10, null=True
                    ),
                ),
                ("max_patients_per_day", models.PositiveIntegerField(default=20)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="%(class)s",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "doctor_profile",
            },
        ),
        migrations.CreateModel(
            name="NurseProfile",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("qualification", models.CharField(max_length=255)),
                ("years_of_experience", models.PositiveIntegerField()),
                ("certification_number", models.CharField(blank=True, max_length=100)),
                ("specialty_notes", models.TextField(blank=True)),
                ("nurse_license", models.CharField(max_length=50, unique=True)),
                ("ward_specialty", models.CharField(max_length=100)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="%(class)s",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "nurse_profile",
            },
        ),
        migrations.CreateModel(
            name="ShiftPattern",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("shift_type", models.CharField(max_length=20)),
                ("start_time", models.TimeField()),
                ("end_time", models.TimeField()),
                ("min_staff", models.IntegerField()),
                ("break_duration", models.DurationField()),
                (
                    "department",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="shift_pattern",
                        to="staff.department",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="StaffTransfer",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "transfer_type",
                    models.CharField(
                        choices=[
                            ("PERMANENT", "Permanent Transfer"),
                            ("TEMPORARY", "Temporary Cover"),
                            ("ROTATION", "Rotation"),
                            ("EMERGENCY", "Emergency Reassignment"),
                        ]
                    ),
                ),
                ("reason", models.TextField()),
                ("effective_date", models.DateField()),
                ("end_date", models.DateField(blank=True, null=True)),
                ("required_documents", models.JSONField(default=list)),
                ("handover_checklist", models.JSONField(default=dict)),
                ("notice_period", models.IntegerField(default=30)),
                ("transition_notes", models.TextField(blank=True)),
                (
                    "approved_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "from_assignment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="transfers_out",
                        to="staff.departmentmember",
                    ),
                ),
                (
                    "to_assignment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="transfers_in",
                        to="staff.departmentmember",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="TechnicianProfile",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("qualification", models.CharField(max_length=255)),
                ("years_of_experience", models.PositiveIntegerField()),
                ("certification_number", models.CharField(blank=True, max_length=100)),
                ("specialty_notes", models.TextField(blank=True)),
                ("technician_license", models.CharField(max_length=50, unique=True)),
                (
                    "equipment_specialties",
                    models.JSONField(
                        default=list, help_text="List of equipment specialties"
                    ),
                ),
                (
                    "lab_certifications",
                    models.JSONField(
                        default=list, help_text="List of laboratory certifications"
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="%(class)s",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "technician_profile",
            },
        ),
        migrations.CreateModel(
            name="WorkloadAssignment",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("week_start_date", models.DateField()),
                (
                    "scheduled_hours",
                    models.DecimalField(decimal_places=2, max_digits=5),
                ),
                ("actual_hours", models.DecimalField(decimal_places=2, max_digits=5)),
                ("on_call_hours", models.DecimalField(decimal_places=2, max_digits=5)),
                ("notes", models.TextField()),
                ("break_duration", models.DurationField(blank=True, null=True)),
                ("is_overtime", models.BooleanField(default=False)),
                (
                    "shift_type",
                    models.CharField(
                        choices=[
                            ("REGULAR", "Regular"),
                            ("ON_CALL", "On Call"),
                            ("EMERGENCY", "Emergency"),
                        ],
                        max_length=20,
                    ),
                ),
                (
                    "department_member",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to="staff.departmentmember",
                    ),
                ),
            ],
        ),
        migrations.AddIndex(
            model_name="department",
            index=models.Index(
                fields=["name", "is_active"], name="department_name_3a7f70_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="department",
            index=models.Index(
                fields=["department_head"], name="department_departm_4c0f44_idx"
            ),
        ),
        migrations.AddConstraint(
            model_name="department",
            constraint=models.CheckConstraint(
                condition=models.Q(("name__isnull", False)),
                name="department_name_not_null",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="department",
            unique_together={("code", "name")},
        ),
        migrations.AddIndex(
            model_name="departmentmember",
            index=models.Index(
                fields=["user", "department", "is_active"],
                name="department__user_id_2b3f1a_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="departmentmember",
            index=models.Index(
                fields=["role", "is_active"], name="department__role_ef574d_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="departmentmember",
            index=models.Index(
                fields=["start_date", "end_date", "time_allocation"],
                name="department__start_d_412281_idx",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="departmentmember",
            unique_together={("department", "user", "role")},
        ),
    ]
