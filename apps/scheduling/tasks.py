from celery import shared_task

# scheduling/tasks.py
from celery.utils.log import get_task_logger

from .utils.shift_generator import ShiftGenerator

logger = get_task_logger(__name__)

@shared_task
def generate_shifts():
    try:
        generator = ShiftGenerator()
        count = generator.generate_shifts()
        logger.info(f"Generated {count} shifts")
        return count
    except Exception as e:
        logger.exception("Shift generation failed: %s", str(e))
        raise generate_shifts.retry(exc=e, countdown=300)  # Retry after 5 minutes

@shared_task
def generate_initial_shifts(member_id):
    from .models import DepartmentMember
    member = DepartmentMember.objects.get(id=member_id)
    generator = ShiftGenerator()

    # Generate shifts for first month
    generator.generate_shifts_for_member(member, lookahead_weeks=4)

    # Send confirmation
    # member.user.send_notification(
    #     title="Your Schedule",
    #     message=f"Shifts generated for {member.department.name}"
    # )
