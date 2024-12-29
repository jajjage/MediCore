# Generated by Django 5.1.4 on 2024-12-24 18:16

import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Patient",
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
                ("first_name", models.CharField(max_length=100)),
                (
                    "middle_name",
                    models.CharField(blank=True, max_length=100, null=True),
                ),
                ("last_name", models.CharField(max_length=100)),
                ("date_of_birth", models.DateField()),
                ("gender", models.CharField(max_length=50)),
                ("email", models.EmailField(max_length=254, unique=True)),
                ("phone_primary", models.CharField(max_length=20)),
                (
                    "phone_secondary",
                    models.CharField(blank=True, max_length=20, null=True),
                ),
                ("preferred_language", models.CharField(default="en", max_length=50)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "ssn_encrypted",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
            ],
            options={
                "db_table": "patients",
                "indexes": [
                    models.Index(fields=["email"], name="patients_email_bf0efb_idx"),
                    models.Index(
                        fields=["last_name", "first_name"],
                        name="patients_last_na_ce6411_idx",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="PatientDemographics",
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
                ("blood_type", models.CharField(blank=True, max_length=5, null=True)),
                (
                    "height_cm",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=5, null=True
                    ),
                ),
                (
                    "weight_kg",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=5, null=True
                    ),
                ),
                ("allergies", models.JSONField(blank=True, default=list)),
                ("chronic_conditions", models.JSONField(blank=True, default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "patient",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="demographics",
                        to="patients.patient",
                    ),
                ),
            ],
            options={
                "db_table": "patient_demographics",
            },
        ),
        migrations.CreateModel(
            name="PatientAddress",
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
                ("address_type", models.CharField(max_length=50)),
                ("street_address1", models.CharField(max_length=255)),
                (
                    "street_address2",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
                ("city", models.CharField(max_length=100)),
                ("state", models.CharField(max_length=100)),
                ("postal_code", models.CharField(max_length=20)),
                ("country", models.CharField(default="United States", max_length=100)),
                ("is_primary", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "patient",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="addresses",
                        to="patients.patient",
                    ),
                ),
            ],
            options={
                "db_table": "patient_addresses",
                "indexes": [
                    models.Index(
                        fields=["postal_code"], name="patient_add_postal__1b2093_idx"
                    )
                ],
            },
        ),
    ]
