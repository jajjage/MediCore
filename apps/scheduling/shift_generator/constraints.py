# shift_generator/constraints.py

import datetime


def is_nurse_available(nurse, date, availability_list):
    """
    Check if a nurse is available on a given date.

    :param nurse: DepartmentMember instance.
    :param date: datetime.date instance.
    :param availability_list: List of NurseAvailability objects for the nurse.
    :return: True if available; False otherwise.
    """
    for availability in availability_list:
        if availability.start_date <= date <= availability.end_date and availability.availability_status in ["unavailable", "preferred_off"]:
                return False
    return True

def check_consecutive_shifts(nurse_state, date, max_consecutive):
    """
    Check if assigning a shift on 'date' would exceed the maximum consecutive shift days.

    :param nurse_state: A UserShiftState instance (or None if no previous shifts).
    :param date: The date of the new shift.
    :param max_consecutive: Maximum allowed consecutive days.
    :return: True if assigning is allowed, False otherwise.
    """
    if nurse_state is None or nurse_state.last_shift_end is None:
        return True  # No history; allow assignment.
    last_date = nurse_state.last_shift_end.date()
    # If the date is consecutive (i.e., one day after the last shift)
    return not ((date - last_date).days == 1 and nurse_state.consecutive_weeks + 1 > max_consecutive)

def update_consecutive_shifts(nurse_state, date):
    """
    Update the nurse_state's consecutive shift counter based on a new assignment.

    :param nurse_state: A UserShiftState instance.
    :param date: The date of the new shift.
    """
    if nurse_state.last_shift_end is None or (date - nurse_state.last_shift_end.date()).days > 1:
        # Reset counter if there was a break
        nurse_state.consecutive_weeks = 1
    else:
        nurse_state.consecutive_weeks += 1
    # Update last shift end to the new date (assuming end of day)
    nurse_state.last_shift_end = datetime.datetime.combine(date, datetime.time.max)
    nurse_state.save()
