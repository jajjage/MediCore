# Generated by Django 5.1.4 on 2025-01-12 13:27

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("tenants", "0001_initial"),
    ]

    operations = [
        migrations.RenameField(
            model_name="client",
            old_name="status",
            new_name="subscription_plan",
        ),
    ]