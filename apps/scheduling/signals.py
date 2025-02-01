from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import GeneratedShift
from .services.schedule_service import SchedulePatternService


@receiver([post_save, post_delete], sender=GeneratedShift)
def invalidate_schedule_cache(sender, instance, **kwargs):
    SchedulePatternService.invalidate_cache(instance.user_id)
