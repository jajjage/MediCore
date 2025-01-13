# Generated by Django 5.1.4 on 2025-01-10 14:18

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("patients", "0003_remove_historicalpatientappointment_color_code_and_more"),
        ("staff", "0007_remove_staffmember_username_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="historicalpatientappointment",
            name="department",
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                limit_choices_to={"department_type__name": "Clinical"},
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to="staff.department",
            ),
        ),
        migrations.AddField(
            model_name="patientappointment",
            name="department",
            field=models.ForeignKey(
                limit_choices_to={"department_type__name": "Clinical"},
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="appointment_department",
                to="staff.department",
            ),
        ),
    ]