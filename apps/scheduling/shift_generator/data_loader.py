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

    :param department_id: ID of the department
    :param target_date: Target date for scheduling
    :return: Dictionary of loaded scheduling data
    """
    # Implementation remains the same as in the previous code
    # (The load_department_data function you provided earlier)
    department = Department.objects.get(id=department_id)

    active_members = DepartmentMember.objects.filter(
        department=department,
        is_active=True,
        end_date__isnull=False
    )
    print(f"active members: {active_members}")
    year, month = target_date.year, target_date.month
    month_start = datetime.date(year, month, 1)
    month_end = datetime.date(year, month, 28)  # Simplified end-of-month

    shift_templates = ShiftTemplate.objects.filter(
        department=department,
        is_active=True,
        valid_from__lte=month_end,
    ).filter(
        Q(valid_until__gte=month_start) | Q(valid_until__isnull=True)
    )

    availabilities = {}
    for member in active_members:
        nurse_avail = list(NurseAvailability.objects.filter(
            user=member.user,
            start_date__lte=month_end,
            end_date__gte=month_start
        ))
        availabilities[member.user.id] = nurse_avail

    print(f"Loaded {len(availabilities)} nurse availabilities")
    shift_states = {}
    for member in active_members:
        try:
            state = UserShiftState.objects.get(user=member.user, department=department)
        except UserShiftState.DoesNotExist:
            state = None
        shift_states[member.user.id] = state

    user_preferences = {}
    for member in active_members:
        try:
            pref = UserShiftPreference.objects.get(user=member.user, department=department)
        except UserShiftPreference.DoesNotExist:
            pref = None
        user_preferences[member.user.id] = pref

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
