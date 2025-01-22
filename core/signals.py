from django.db.models.signals import m2m_changed, post_delete, post_save
from django.dispatch import receiver

from core.models import MyUser, TenantMembership


@receiver([post_save, m2m_changed], sender=TenantMembership)
def clear_membership_cache(sender, instance, **kwargs):
    instance.user.clear_permission_cache()

@receiver([post_save, post_delete], sender=MyUser.groups.through)
def invlidate_group_cache(sender, instance, **kwargs):
    if isinstance(instance, MyUser):
        instance.user.clear_permission_cache()
