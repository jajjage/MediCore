from django.db.models.signals import m2m_changed, post_delete, post_save
from django.dispatch import receiver

from core.models import HospitalMembership


@receiver([post_save, post_delete], sender=HospitalMembership)
def clear_membership_cache(sender, instance, **kwargs):
    if instance.user:
        instance.user.clear_permission_cache()

@receiver(m2m_changed, sender=HospitalMembership.groups.through)
def invlidate_group_cache(sender, instance, action, **kwargs):
    if instance.user and action in ["post_add", "post_clear", "post_remove"]:
        instance.user.clear_permission_cache()
