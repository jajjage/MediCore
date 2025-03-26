import datetime

from django.db.models import Q

from apps.scheduling.models import (
    NurseAvailability,
    ShiftTemplate,
    UserShiftPreference,
    UserShiftState,
    WeekendShiftPolicy,
)
from apps.staff.models import Department, DepartmentMember


def load_department_data(department_id, target_date):
    """
    Load all required data for scheduling including user preferences and weekend policy.
    """
    # Load the department.
    print(f"Dept id: {department_id}")
    department = Department.objects.get(id=department_id)

    # Load active department members.
    active_members = DepartmentMember.objects.filter(
        department=department,
        is_active=True,
        end_date__isnull=False
    )
    print(f"Active members: {active_members}")
    # Determine the month boundaries.
    year, month = target_date.year, target_date.month
    month_start = datetime.date(year, month, 1)
    month_end = datetime.date(year, month, 28)  # Simplified end-of-month.
    print(f"Month start: {month_start}, Month end: {month_end}")
    # Load shift templates active in the target period.
    shift_templates = ShiftTemplate.objects.filter(
        department=department,
        is_active=True,
        valid_from__lte=month_end,
    ).filter(
        Q(valid_until__gte=month_start) | Q(valid_until__isnull=True)
    )
    print(f"Shift templates: {shift_templates}")
    # Build nurse availabilities keyed by user ID.
    availabilities = {}
    for member in active_members:
        nurse_avail = list(NurseAvailability.objects.filter(
            user=member.user,
            start_date__lte=month_end,
            end_date__gte=month_start
        ))
        availabilities[member.user.id] = nurse_avail

    # Load user shift state for each active member.
    shift_states = {}
    for member in active_members:
        try:
            state = UserShiftState.objects.get(user=member.user, department=department)
        except UserShiftState.DoesNotExist:
            state = None
        shift_states[member.user.id] = state

    # Load user shift preferences for each active member.
    user_preferences = {}
    for member in active_members:
        try:
            pref = UserShiftPreference.objects.get(user=member.user, department=department)
        except UserShiftPreference.DoesNotExist:
            pref = None
        user_preferences[member.user.id] = pref

    # Load weekend shift policy for the department.
    try:
        weekend_policy = WeekendShiftPolicy.objects.get(department=department)
    except WeekendShiftPolicy.DoesNotExist:
        weekend_policy = None

    return {
        "department": department,
        "active_members": list(active_members),
        "shift_templates": list(shift_templates),
        "availabilities": availabilities,
        "shift_states": shift_states,
        "user_preferences": user_preferences,
        "weekend_policy": weekend_policy,
    }
