from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Client


@receiver([post_save, post_delete], sender=Client)
def invalidate_domain_cache(sender, **kwargs):
    # Invalidate entire cache on any Client change
    cache.delete("active_subdomains_dict")

