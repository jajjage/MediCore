# Generated by Django 5.1.4 on 2025-03-27 13:34

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("scheduling", "0003_alter_usershiftstate_last_shift_end"),
    ]

    operations = [
        migrations.AlterField(
            model_name="usershiftstate",
            name="current_template",
            field=models.ForeignKey(
                blank=True,
                help_text="Current shift template used by the nurse. Updated after each assignment.",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="scheduling.shifttemplate",
            ),
        ),
    ]
