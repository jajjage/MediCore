# Generated by Django 5.1.4 on 2024-12-31 15:36

import django.db.models.deletion
import django.utils.timezone
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('hospital', '0002_alter_hospitalprofile_admin_user'),
    ]

    operations = [
        migrations.CreateModel(
            name='Department',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=100)),
                ('hospital', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='hospital.hospitalprofile')),
            ],
            options={
                'db_table': 'department',
            },
        ),
        migrations.CreateModel(
            name='StaffRole',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=100)),
                ('code', models.CharField(max_length=50, unique=True)),
                ('permissions', models.ManyToManyField(blank=True, related_name='staff_roles', to='auth.permission')),
            ],
            options={
                'db_table': 'staff_staffrole',
            },
        ),
        migrations.CreateModel(
            name='StaffMember',
            fields=[
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('email', models.EmailField(max_length=254, unique=True)),
                ('first_name', models.CharField(max_length=30)),
                ('last_name', models.CharField(max_length=30)),
                ('is_active', models.BooleanField(default=True)),
                ('is_staff', models.BooleanField(default=True)),
                ('department', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='staff.department')),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to.', related_name='staff_members', to='auth.group', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='staff_members', to='auth.permission', verbose_name='user permissions')),
                ('role', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='staff.staffrole')),
            ],
            options={
                'db_table': 'staff_member',
                'permissions': [('can_view_staff', 'Can view staff members'), ('can_manage_staff', 'Can manage staff members')],
            },
        ),
    ]
