# Generated by Django 5.1.4 on 2025-01-24 23:03

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("tenants", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="HospitalMembership",
            fields=[
                ("is_deleted", models.BooleanField(default=False)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("is_tenant_admin", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "tenant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="hospital_memberships_tenant",
                        to="tenants.client",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="hospital_memberships_user",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "hospital_memberships",
            },
        ),
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
                ("hospital_name", models.CharField(max_length=200, unique=True)),
                ("license_number", models.CharField(max_length=100, unique=True)),
                ("contact_email", models.EmailField(max_length=254)),
                ("contact_phone", models.CharField(max_length=20)),
                ("address", models.TextField(blank=True)),
                ("specialty", models.CharField(blank=True, max_length=100)),
                ("bed_capacity", models.PositiveIntegerField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "staff",
                    models.ManyToManyField(
                        blank=True,
                        related_name="associated_hospitals",
                        through="hospital.HospitalMembership",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "tenant",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="hospital_profile",
                        to="tenants.client",
                    ),
                ),
            ],
            options={
                "db_table": "hospital_profile",
            },
        ),
        migrations.AddField(
            model_name="hospitalmembership",
            name="hospital_profile",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="hospital_memberships_profile",
                to="hospital.hospitalprofile",
            ),
        ),
        migrations.CreateModel(
            name="Role",
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
                ("name", models.CharField(max_length=50, unique=True)),
                ("description", models.TextField(blank=True, null=True)),
                ("code", models.CharField(max_length=50, unique=True)),
                ("is_active", models.BooleanField(default=True)),
                ("groups", models.ManyToManyField(blank=True, to="auth.group")),
                (
                    "permissions",
                    models.ManyToManyField(blank=True, to="auth.permission"),
                ),
            ],
            options={
                "db_table": "hospital_role",
            },
        ),
        migrations.AddField(
            model_name="hospitalmembership",
            name="role",
            field=models.ForeignKey(
                default=None,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="hospital_memberships_role",
                to="hospital.role",
            ),
        ),
        migrations.AddIndex(
            model_name="role",
            index=models.Index(
                fields=["name", "is_active"], name="hospital_ro_name_4b7b2d_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="role",
            index=models.Index(fields=["code"], name="hospital_ro_code_b934a1_idx"),
        ),
        migrations.AddIndex(
            model_name="hospitalmembership",
            index=models.Index(
                fields=["tenant", "role", "is_deleted"],
                name="hospital_me_tenant__39c322_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="hospitalmembership",
            index=models.Index(
                fields=["user", "hospital_profile", "is_tenant_admin"],
                name="hospital_me_user_id_6768ea_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="hospitalmembership",
            index=models.Index(
                fields=["created_at", "is_deleted"],
                name="hospital_me_created_d05f03_idx",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="hospitalmembership",
            unique_together={("user", "hospital_profile", "tenant")},
        ),
    ]
