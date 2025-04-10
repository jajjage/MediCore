from datetime import timedelta

from django.db.models import Sum
from django.utils import timezone

from apps.scheduling.models import GeneratedShift, UserShiftHistory

WEEKEND_START = 5
def get_max_staff(template, date):
    return template.max_staff_weekend if date.weekday() >= WEEKEND_START else template.max_staff_weekday

def check_fatigue(user, new_shift_start):
    last_shift = GeneratedShift.objects.filter(
        user=user
    ).order_by("-end_datetime").first()

    if not last_shift:
        return True

    min_gap = last_shift.template.min_shift_gap
    return (new_shift_start - last_shift.end_datetime) >= min_gap

def check_cooldown(user, template):
    last_usage = UserShiftHistory.objects.filter(
        user=user,
        template=template
    ).order_by("-worked_date").first()

    if not last_usage:
        return True

    cooldown_end = last_usage.worked_date + timedelta(weeks=template.cooldown_weeks)
    return timezone.now().date() > cooldown_end

def check_overtime(user, week_start):
    from apps.staff.models import WorkloadAssignment
    total_hours = WorkloadAssignment.objects.filter(
        generated_shift__user=user,
        generated_shift__start_datetime__week=week_start
    ).aggregate(Sum("scheduled_hours"))["scheduled_hours__sum"] or 0

    return total_hours > user.department_members.get().max_weekly_hours

# utils.py
def fatigue_risk(user):
    from apps.staff.models import GeneratedShift
    last_shift = GeneratedShift.objects.filter(
        user=user,
        end_datetime__lt=timezone.now()
    ).order_by("-end_datetime").first()

    if last_shift:
        rest_hours = (timezone.now() - last_shift.end_datetime).total_seconds() / 3600
        return rest_hours < user.department_members.get().rest_period_hours
    return False


def create_emergency_shift(doctor, start, end):
    GeneratedShift.objects.create(
        user=doctor,
        start_datetime=start,
        end_datetime=end,
        status="EMERGENCY",
        is_override=True
    )
    # Automatically cancel conflicting shifts
    GeneratedShift.objects.filter(
        user=doctor,
        start_datetime__lt=end,
        end_datetime__gt=start
    ).update(status="CANCELLED")



