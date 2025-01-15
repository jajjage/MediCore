# Generated by Django 5.1.4 on 2025-01-14 14:47

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("core", "0001_initial"),
        ("tenants", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="HospitalProfile",
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
                    "subscription_plan",
                    models.CharField(
                        choices=[
                            ("trial", "Trial"),
                            ("basic", "Basic"),
                            ("premium", "Premium"),
                        ],
                        max_length=20,
                    ),
                ),
                ("hospital_name", models.CharField(max_length=200)),
                ("license_number", models.CharField(max_length=100, unique=True)),
                ("contact_email", models.EmailField(max_length=254)),
                ("contact_phone", models.CharField(max_length=20)),
                ("address", models.TextField(blank=True)),
                ("specialty", models.CharField(blank=True, max_length=100)),
                ("bed_capacity", models.PositiveIntegerField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "admin_user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="administered_hospital",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "tenant",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="profile",
                        to="tenants.client",
                    ),
                ),
            ],
            options={
                "db_table": "hospital_profile",
            },
        ),
        migrations.CreateModel(
            name="HospitalStaffMembership",
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
                ("joined_date", models.DateTimeField(auto_now_add=True)),
                ("is_active", models.BooleanField(default=True)),
                (
                    "hospital",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="hospital.hospitalprofile",
                    ),
                ),
                (
                    "tenant_permission",
                    models.ForeignKey(
                        help_text="The staff member's role and permissions in this hospital",
                        on_delete=django.db.models.deletion.CASCADE,
                        to="core.tenantpermission",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "hospital_staff_membership",
                "unique_together": {("hospital", "user")},
            },
        ),
        migrations.AddField(
            model_name="hospitalprofile",
            name="additional_staff",
            field=models.ManyToManyField(
                blank=True,
                related_name="associated_hospitals",
                through="hospital.HospitalStaffMembership",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
