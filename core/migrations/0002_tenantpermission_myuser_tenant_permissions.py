# Generated by Django 5.1.4 on 2025-01-12 11:45

import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
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
            ],
            options={
                "db_table": "core_tenant_permission",
                "unique_together": {("schema_name",)},
            },
        ),
        migrations.AddField(
            model_name="myuser",
            name="tenant_permissions",
            field=models.ManyToManyField(
                related_name="tenant_admin", to="core.tenantpermission"
            ),
        ),
    ]