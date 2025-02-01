# Signals.py
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.patients.services.appointment_service import SchedulePatternService

from .models import GeneratedShift, WorkloadAssignment


@receiver(post_save, sender=GeneratedShift)
def create_workload_record(sender, instance, created, **kwargs):
    if created:
        duration = instance.end_datetime - instance.start_datetime
        WorkloadAssignment.objects.create(
            generated_shift=instance,
            scheduled_hours=duration.total_seconds() / 3600
        )

