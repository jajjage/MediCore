from celery import shared_task
from celery.utils.log import get_task_logger
from django import db
from django.contrib.auth import get_user_model
from django.db import DatabaseError, OperationalError
from django_tenants.utils import schema_context

from .utils.shift_generator import ShiftGenerator

logger = get_task_logger(__name__)

User = get_user_model()

@shared_task(bind=True, max_retries=3)
def generate_daily_shifts(self, tenant_schema):
    with schema_context(tenant_schema):
        try:
            generator = ShiftGenerator(lookahead_weeks=4)
            # For daily generation, you can omit generation_end_date to use the default batch_days
            count = generator.generate_department_shifts(initial_setup=False)
            return f"Generated {count} shifts"
        except (DatabaseError, OperationalError) as e:
            # Retry logic etc.
            raise self.retry(exc=e, countdown=5)


@shared_task(bind=True, max_retries=3)
def initialize_department_shifts(self, tenant_schema):
    with schema_context(tenant_schema):
        try:
            generator = ShiftGenerator()  # This will use the default lookahead if needed.
            count = generator.generate_department_shifts(initial_setup=True)
            return f"Generated {count} shifts"
        except (DatabaseError, OperationalError) as e:
            raise self.retry(exc=e, countdown=5)
