# Generated by Django 5.1.4 on 2025-02-01 12:36

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("scheduling", "0002_initial"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="shifttemplate",
            name="type",
        ),
    ]
