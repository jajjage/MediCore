# /scheduler.py
from __future__ import annotations

import datetime
import logging
from typing import TYPE_CHECKING, Any, NamedTuple, Optional

from apps.scheduling.models import GeneratedShift

from .calendar import build_month_calendar
from .constraints import (
    check_consecutive_shifts,
    is_nurse_available,
    update_consecutive_shifts,
)
from .data_loader import load_department_data

logger = logging.getLogger(__name__)


class SchedulerContext(NamedTuple):
    availabilities: Any
    shift_states: Any
    user_preferences: Any
    weekend_policy: Any

def select_nurses_for_template(nurses, context, date, template, required_staff):
    """
    Select eligible nurses for a given shift template on a specific date.

    This function uses a SchedulerContext namedtuple to access:
      - availabilities: Dict mapping user IDs to NurseAvailability lists.
      - shift_states: Dict mapping user IDs to UserShiftState instances.
      - user_preferences: Dict mapping user IDs to UserShiftPreference instances.
      - weekend_policy: A WeekendShiftPolicy instance (or None).

    :param nurses: List of DepartmentMember instances.
    :param context: SchedulerContext with availabilities, shift_states, user_preferences, weekend_policy.
    :param date: The date of the shift.
    :param template: A ShiftTemplate instance.
    :param required_staff: Number of nurses required.
    :return: A list of DepartmentMember instances.
    """
    eligible_nurses = []

    for nurse in nurses:
        user_id = nurse.user.id
        nurse_avail = context.availabilities.get(user_id, [])
        nurse_state = context.shift_states.get(user_id)
        preference = context.user_preferences.get(user_id)

        # Check hard availability.
        if not is_nurse_available(nurse, date, nurse_avail):
            continue

        # Check consecutive shift limits.
        if not check_consecutive_shifts(nurse_state, date, template.max_consecutive_weeks):
            continue

        # Check role/skill matching.
        if template.required_role not in {nurse.role, "ANY"}:
            continue

        # --- New: Check User Preferences ---
        if preference and preference.preferred_shift_types.exists() and template not in preference.preferred_shift_types.all():
            # Option: Skip nurse if template is not in their preferred types.
            continue

        # --- New: Check Weekend Shift Policy ---
        weekday_str = date.strftime("%a").upper()  # e.g., "MON", "TUE"
        is_weekend = weekday_str in ["SAT", "SUN"]
        if is_weekend and context.weekend_policy:
            # Assume nurse_state has an attribute `weekend_shift_count` that tracks weekend shifts.
            weekend_count = getattr(nurse_state, "weekend_shift_count", 0)
            if weekend_count >= context.weekend_policy.max_weekend_shifts:
                continue  # Skip nurse if already reached the maximum weekend shifts.

        eligible_nurses.append(nurse)
        if len(eligible_nurses) >= required_staff:
            break

    return eligible_nurses

def create_generated_shift(nurse, department, date, template):
    """
    Create and save a GeneratedShift based on the provided nurse, department, date, and template.
    """
    # Combine the date with the template's start and end times.
    start_dt = datetime.datetime.combine(date, template.start_time)
    end_dt = datetime.datetime.combine(date, template.end_time)
    if end_dt <= start_dt:  # Adjust for overnight shifts.
        end_dt += datetime.timedelta(days=1)

    shift = GeneratedShift.objects.create(
        user=nurse.user,
        department=department,
        start_datetime=start_dt,
        end_datetime=end_dt,
        source_template=template,
        status=GeneratedShift.Status.SCHEDULED,
        penalty_score=0.0  # Starting penalty score.
    )
    return shift

def generate_schedule(department_id, year, month):
    """
    Generate a monthly schedule for the specified department.

    Steps:
      1. Load all required data.
      2. Build the month's calendar.
      3. For each day, determine applicable shift templates.
      4. For each template, select eligible nurses and create shift assignments.
      5. Update nurse shift state accordingly.
    """
    target_date = datetime.date(year, month, 1)
    data = load_department_data(department_id, target_date)
    department = data["department"]
    nurses = data["active_members"]
    templates = data["shift_templates"]
    availabilities = data["availabilities"]
    shift_states = data["shift_states"]
    user_preferences = data["user_preferences"]
    weekend_policy = data["weekend_policy"]

    # Build the calendar for the month.
    month_calendar = build_month_calendar(year, month)
    logger.info(f"Generating schedule for Department {department} for {year}-{month}")

    # Bundle the extra parameters in a SchedulerContext.
    context = SchedulerContext(
        availabilities=availabilities,
        shift_states=shift_states,
        user_preferences=user_preferences,
        weekend_policy=weekend_policy
    )
    print(f"template: {templates}")

    for day_info in month_calendar:
        date = day_info["date"]
        day_type = day_info["day_type"]
        logger.debug(f"Processing {date} ({day_type})")

        # Determine applicable templates for the day.
        applicable_templates = []
        for template in templates:
            if template.recurrence == "WEEKLY":

                days = template.recurrence_parameters.get("days", [])
                weekday_str = date.strftime("%a")  # e.g., "MON", "TUE"
                if weekday_str in days:
                    applicable_templates.append(template)
            else:
                applicable_templates.append(template)

        for template in applicable_templates:
            required_staff = template.max_staff_weekday if day_type == "weekday" else template.max_staff_weekend
            if required_staff <= 0:
                continue

            eligible_nurses = select_nurses_for_template(
                nurses,
                context,
                date,
                template,
                required_staff
            )
            logger.info(f"On {date}: Template '{template.name}' requires {required_staff} staff; {len(eligible_nurses)} eligible found.")

            for nurse in eligible_nurses:
                shift = create_generated_shift(nurse, department, date, template)
                logger.info(f"Created shift {shift.id} for nurse {nurse.user.first_name} on {date} using template '{template.name}'")
                # Update the nurse's shift state.
                nurse_state = context.shift_states.get(nurse.user.id)
                if nurse_state:
                    update_consecutive_shifts(nurse_state, date)
                # Optionally update weekend shift count if it's a weekend.
                if date.strftime("%a") in ["Sat", "Sun"] and nurse_state:
                    # For illustration, increment the weekend shift count.
                    current_count = getattr(nurse_state, "weekend_shift_count", 0)
                    nurse_state.weekend_shift_count = current_count + 1
                    nurse_state.save()

    logger.info("Monthly schedule generation complete.")
