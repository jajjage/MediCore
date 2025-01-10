# Generated by Django 5.1.4 on 2025-01-10 13:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("staff", "0006_staffmember_username_alter_staffmember_is_staff"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="staffmember",
            name="username",
        ),
        migrations.AlterField(
            model_name="staffmember",
            name="is_staff",
            field=models.BooleanField(
                default=False,
                help_text="Designates whether the user can log into this admin site.",
                verbose_name="staff status",
            ),
        ),
    ]
