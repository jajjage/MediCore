# Generated by Django 5.1.4 on 2025-01-26 12:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0003_myuser_groups_myuser_user_permissions"),
    ]

    operations = [
        migrations.AddField(
            model_name="myuser",
            name="middle_name",
            field=models.CharField(blank=True, max_length=150),
        ),
    ]
