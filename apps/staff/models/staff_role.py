import uuid

from django.db import models

from .department_member import DepartmentMember


class StaffRole(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, unique=True, db_index=True)
    permissions = models.ManyToManyField(
        "auth.Permission", blank=True, related_name="staff_roles"
    )
    description = models.TextField(blank=True)
    category = models.CharField(
        max_length=50,
        choices=[
            ("MEDICAL", "Medical Staff"),
            ("NURSING", "Nursing Staff"),
            ("ADMIN", "Administrative Staff"),
            ("SUPPORT", "Support Staff")
        ]
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "staff_staffrole"
        indexes = [
            models.Index(fields=["name", "is_active"]),
        ]

    def __str__(self):
        return self.name

    def get_staff_count(self):
        """Get count of staff with this role."""
        return DepartmentMember.objects.filter(role=self.code, is_active=True).count()
