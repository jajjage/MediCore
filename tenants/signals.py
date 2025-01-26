from django.core.cache import cache
from django.core.management import call_command
from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Client


@receiver(post_save, sender=Client)
def setup_tenant_schema(sender, instance, created, **kwargs):
    if created:
        transaction.on_commit(
            lambda: call_command("create_index", schema=instance.schema_name)
        )
@receiver([post_save, post_delete], sender=Client)
def invalidate_domain_cache(sender, **kwargs):
    # Invalidate entire cache on any Client change
    cache.delete("active_subdomains_dict")

