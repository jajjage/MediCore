# shift_generator/constraints.py

import datetime
from typing import TYPE_CHECKING

from apps.scheduling.models import GeneratedShift, UserShiftState
from apps.staff.models.department_member import DepartmentMember


def ensure_user_state(nurse: DepartmentMember, department, shift_states: dict) -> UserShiftState:
    """
    Ensure that a UserShiftState exists for the nurse.

    If it doesn't, create a new one with default values.
    """
    user_id = nurse.user.id
    state = shift_states.get(user_id)
    if not state:
        state = UserShiftState.objects.create(
            user=nurse.user,
            department=department,
            current_template=None,
            last_shift_end=None,
            rotation_index=0,
            consecutive_weeks=0,
            cooldowns={},
            weekend_shift_count=0  # Add tracking for weekend shifts
        )
        shift_states[user_id] = state
    return state

def is_nurse_already_assigned(nurse, date, template=None):
    """
    Check if a nurse is already assigned to a shift on the given date.

    :param nurse: DepartmentMember instance
    :param date: Date to check
    :param template: Optional specific template to check against
    :return: Boolean indicating if nurse is already assigned
    """
    query = GeneratedShift.objects.filter(
        user=nurse.user,
        start_datetime__date=date
    )

    if template:
        query = query.filter(source_template=template)

    return query.exists()

def is_nurse_available(nurse, date, nurse_avail):
    """
    Check if a nurse is available on the given date.

    :param nurse: DepartmentMember instance
    :param date: Date to check
    :param nurse_avail: List of nurse availability records
    :return: Boolean indicating availability
    """
    # Implement availability check logic
    for availability in nurse_avail:
        if availability.start_date <= date <= availability.end_date:
            return True
    return False

def check_consecutive_shifts(nurse_state, date, max_consecutive_weeks):
    """
    Check if the nurse can take another shift based on consecutive shift limits.

    :param nurse_state: UserShiftState instance
    :param date: Date of potential shift
    :param max_consecutive_weeks: Maximum consecutive weeks allowed
    :return: Boolean indicating if shift is allowed
    """
    if nurse_state.consecutive_weeks >= max_consecutive_weeks:
        return False
    return True

def update_user_state(nurse_state, date, template):
    """
    Update the user's shift state after assigning a shift.
    
    :param nurse_state: UserShiftState instance
    :param date: Date of the shift
    :param template: ShiftTemplate instance
    """
    # Reset consecutive weeks if template changes
    if nurse_state.current_template != template:
        nurse_state.consecutive_weeks = 1
        nurse_state.current_template = template
    else:
        nurse_state.consecutive_weeks += 1

    nurse_state.last_shift_end = date
    nurse_state.save()
