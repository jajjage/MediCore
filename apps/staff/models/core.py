
import uuid

from django.db import models


class StaffProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    qualification = models.CharField(max_length=255, blank=True, null=True)
    years_of_experience = models.PositiveIntegerField(blank=True, null= True)
    certification_number = models.CharField(max_length=100, blank=True)
    specialty_notes = models.TextField(blank=True)


    class Meta:
        abstract = True


