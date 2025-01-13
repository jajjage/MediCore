# Generated by Django 5.1.4 on 2025-01-12 15:20

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0003_alter_tenantpermission_unique_together_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="myuser",
            name="tenant_permissions",
        ),
        migrations.AlterField(
            model_name="tenantpermission",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="tenant_permissions",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]