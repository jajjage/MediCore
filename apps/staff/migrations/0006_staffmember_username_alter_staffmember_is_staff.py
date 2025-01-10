# Generated by Django 5.1.4 on 2025-01-10 13:15

import django.contrib.auth.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("staff", "0005_alter_staffmember_options_alter_staffmember_groups_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="staffmember",
            name="username",
            field=models.CharField(
                default="jajjage",
                error_messages={"unique": "A user with that username already exists."},
                help_text="Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.",
                max_length=150,
                unique=True,
                validators=[django.contrib.auth.validators.UnicodeUsernameValidator()],
                verbose_name="username",
            ),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="staffmember",
            name="is_staff",
            field=models.BooleanField(default=False),
        ),
    ]
