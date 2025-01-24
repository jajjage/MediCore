
import uuid

from django.conf import settings
from django.db import models


class StaffProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="%(class)s",
    )
    qualification = models.CharField(max_length=255)
    years_of_experience = models.PositiveIntegerField()
    certification_number = models.CharField(max_length=100, blank=True)
    specialty_notes = models.TextField(blank=True)


    class Meta:
        abstract = True


