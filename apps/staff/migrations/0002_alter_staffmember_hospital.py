# Generated by Django 5.1.4 on 2025-01-15 18:32

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hospital", "0001_initial"),
        ("staff", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="staffmember",
            name="hospital",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="staff_hospital",
                to="hospital.hospitalprofile",
            ),
        ),
    ]