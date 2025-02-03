from celery import shared_task
from celery.utils.log import get_task_logger
from django import db
from django.db import DatabaseError, OperationalError
from django_tenants.utils import schema_context

from .utils.shift_generator import ShiftGenerator

logger = get_task_logger(__name__)


@shared_task(bind=True, max_retries=3)
def generate_shifts(self, tenant_schema):
      with schema_context(tenant_schema):
        try:
            generator = ShiftGenerator(lookahead_weeks=2)
            count = generator.generate_shifts()
            return f"Generated {count} shifts"
        except (DatabaseError, OperationalError) as e:
            print(f"Shift generation failed: {e!s}")
            # Retry after 5 seconds instead of 5 minutes for testing
            raise self.retry(exc=e, countdown=5)

@shared_task(bind=True, max_retries=3)
def generate_monthly_shifts(self, tenant_schema):
    """Prime future assignments 3 months ahead."""
    with schema_context(tenant_schema):
        try:
            generator = ShiftGenerator(lookahead_weeks=12)  # ~3 months
            count = generator.generate_shifts(future_mode=True)
            return f"Generated {count} shifts"
        except (DatabaseError, OperationalError) as e:
            print(f"Shift generation failed: {e!s}")
            # Retry after 5 seconds instead of 5 minutes for testing
            raise self.retry(exc=e, countdown=5)
