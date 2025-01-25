from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from hospital.models import HospitalMembership


@receiver([post_save, post_delete], sender=HospitalMembership)
def clear_staff_cache(sender, instance, **kwargs):
    cache.delete(f"hospital_{instance.hospital.id}_staff")
