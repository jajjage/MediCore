from django.db import connection
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django_tenants.models import TenantMixin
from django_tenants.utils import schema_context


@receiver(post_save, sender=TenantMixin)
def create_tenant_pin_sequence(sender, instance, created, **kwargs):
    """Create PIN sequence when new tenant is created."""
    if created:
        with schema_context(instance.schema_name), connection.cursor() as cursor:
            cursor.execute("""
                    CREATE SEQUENCE IF NOT EXISTS patient_pin_seq_middle
                    START WITH 20
                    INCREMENT BY 1
                    MINVALUE 20
                    MAXVALUE 99999
                    CYCLE;
                """)
        # Second sequence for last part (1000-9999)
        cursor.execute("""
                    CREATE SEQUENCE IF NOT EXISTS patient_pin_seq_last
                    START WITH 40
                    INCREMENT BY 1
                    MINVALUE 40
                    MAXVALUE 99999
                    CYCLE;
                """)
        cursor.execute("CREATE INDEX patient_pin_lower_idx ON patients (LOWER(pin));")


