# Generated by Django 5.1.4 on 2025-01-14 14:47

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("contenttypes", "0002_remove_content_type_name"),
        ("tenants", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="MyUser",
            fields=[
                ("password", models.CharField(max_length=128, verbose_name="password")),
                (
                    "last_login",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="last login"
                    ),
                ),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("email", models.EmailField(max_length=254, unique=True)),
                ("is_active", models.BooleanField(default=True)),
                ("is_staff", models.BooleanField(default=True)),
                ("is_tenant_admin", models.BooleanField(default=False)),
                ("is_superuser", models.BooleanField(default=False)),
                ("first_name", models.CharField(blank=True, max_length=150)),
                ("last_name", models.CharField(blank=True, max_length=150)),
                ("phone_number", models.CharField(blank=True, max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "groups",
                    models.ManyToManyField(
                        blank=True,
                        help_text="The groups this user belongs to.",
                        related_name="myuser_set",
                        to="auth.group",
                        verbose_name="groups",
                    ),
                ),
                (
                    "hospital",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="staff_members",
                        to="tenants.client",
                    ),
                ),
                (
                    "user_permissions",
                    models.ManyToManyField(
                        blank=True,
                        help_text="Specific permissions for this user.",
                        related_name="myuser_set",
                        to="auth.permission",
                        verbose_name="user permissions",
                    ),
                ),
            ],
            options={
                "db_table": "core_user",
            },
        ),
        migrations.CreateModel(
            name="TenantPermission",
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
                ("schema_name", models.CharField(max_length=63)),
                (
                    "permission_type",
                    models.CharField(
                        choices=[
                            ("ADMIN", "Admin"),
                            ("STAFF", "Staff"),
                            ("VIEWER", "Viewer"),
                        ],
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="tenant_permissions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "core_tenant_permission",
                "unique_together": {("user", "schema_name")},
            },
        ),
        migrations.CreateModel(
            name="ModelPermission",
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
                    "permission_type",
                    models.CharField(
                        choices=[
                            ("view", "Can View"),
                            ("add", "Can Add"),
                            ("change", "Can Change"),
                            ("delete", "Can Delete"),
                        ],
                        help_text="The type of permission granted",
                        max_length=10,
                    ),
                ),
                (
                    "content_type",
                    models.ForeignKey(
                        help_text="The model this permission applies to",
                        on_delete=django.db.models.deletion.CASCADE,
                        to="contenttypes.contenttype",
                    ),
                ),
                (
                    "tenant_permission",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="model_permissions",
                        to="core.tenantpermission",
                    ),
                ),
            ],
            options={
                "db_table": "core_model_permission",
                "unique_together": {
                    ("tenant_permission", "content_type", "permission_type")
                },
            },
        ),
    ]
