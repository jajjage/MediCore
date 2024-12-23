from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser
from django.utils.translation import gettext_lazy as _

class MyUserManager(BaseUserManager):
    def create_user(self, email, role, password=None, staff_role=None):
        """
        Creates and saves a User with the given email, date of birth, role, and password.
        """
        if not email:
            raise ValueError("Users must have an email address")
        if not role:
            raise ValueError("Users must have a role")

        user = self.model(
            email=self.normalize_email(email),
            role=role,
        )
        if role != "patient" and not staff_role:
            raise ValueError("Staff must have a staff role")
        user.staff_role = staff_role
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None):
        """
        Creates and saves a superuser with the given email, date of birth, and password.
        """
        user = self.create_user(
            email=email,
            role='admin',
            staff_role='admin',
            password=password,
        )
        user.is_admin = True
        user.is_superuser = True
        user.save(using=self._db)
        return user

    def create_doctor(self, email, password=None):
        return self.create_user(
            email=email,
            role="staff",
            staff_role="doctor",
            password=password,
        )

    def create_nurse(self, email, date_of_birth, password=None):
        return self.create_user(
            email=email,
            date_of_birth=date_of_birth,
            role="staff",
            staff_role="nurse",
            password=password,
        )


class MyUser(AbstractBaseUser):
    ROLES = [
        ('staff', _('Staff')),
        ('patient', _('Patient')),
    ]

    STAFF_ROLES = [
        ('admin', _('Admin')),
        ('doctor', _('Doctor')),
        ('nurse', _('Nurse')),
    ]

    email = models.EmailField(
        verbose_name="email address",
        max_length=255,
        unique=True,
    )

    role = models.CharField(max_length=10, choices=ROLES)
    staff_role = models.CharField(
        max_length=10, choices=STAFF_ROLES, null=True, blank=True
    )
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    objects = MyUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["date_of_birth", "role"]

    def __str__(self):
        return self.email

    def has_perm(self, perm, obj=None):
        """
        Does the user have a specific permission?
        """
        if self.is_admin or self.is_superuser:
            return True
        return False

    def has_module_perms(self, app_label):
        """
        Does the user have permissions to view the app `app_label`?
        """
        if self.is_admin or self.is_superuser:
            return True
        return False

    @property
    def is_staff(self):
        """
        Is the user a member of staff?
        """
        return self.role == "staff"
