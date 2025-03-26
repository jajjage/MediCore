from celery import shared_task
from celery.utils.log import get_task_logger
from django import db
from django.contrib.auth import get_user_model
from django.db import DatabaseError, OperationalError, connection
from django_tenants.utils import schema_context

from apps.scheduling.models import ShiftSwapRequest
from apps.scheduling.shift_swap.swap_engine import process_swap_request

from .shift_generator.scheduler import generate_schedule

logger = get_task_logger(__name__)

User = get_user_model()

@shared_task(bind=True, max_retries=3)
def generate_initial_shifts(self, department_id, year, month, schema_name):
    with schema_context(schema_name):
        try:
            generate_schedule(department_id, year, month)
        except (DatabaseError, OperationalError) as e:
            # Retry logic etc.
            logger.exception(f"Error generating shifts: {e}")

@shared_task(bind=True, max_retries=3)
def process_swap_request_task(swap_request_id, tenant_schema):
    with schema_context(tenant_schema):
        try:
            swap_request = ShiftSwapRequest.objects.get(id=swap_request_id)
            process_swap_request(swap_request)
        except ShiftSwapRequest.DoesNotExist:
            # Handle error accordingly
            pass
