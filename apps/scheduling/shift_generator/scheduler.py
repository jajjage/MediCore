from __future__ import annotations

import datetime
import logging
from typing import TYPE_CHECKING, Any, List, NamedTuple, Optional

from django.db import DatabaseError
from django.db.models import Q
from django.utils import timezone

from apps.scheduling.models import (
    GeneratedShift,
    NurseAvailability,
    ShiftTemplate,
    WeekendShiftPolicy,
)

from .data_loader import load_department_data

if TYPE_CHECKING:
    from apps.staff.models import Department, DepartmentMember

logger = logging.getLogger(__name__)

MIN_REQUIRED_TEMPLATES = 2

class SchedulerContext(NamedTuple):
    availabilities: dict
    shift_states: dict
    user_preferences: dict
    weekend_policy: WeekendShiftPolicy | None

class NurseEligibilityChecker:
    """
    Centralized class for checking nurse eligibility for shifts with support for.

    weekly rotations between nurse groups.
    """

    @staticmethod
    def is_nurse_available(
        nurse: DepartmentMember,  # noqa: ARG004
        date: datetime.date,
        availabilities: list[NurseAvailability]
    ) -> bool:
        """
        Check if a nurse is available on the given date.

        :param nurse: Nurse to check
        :param date: Date to verify availability
        :param availabilities: List of availability records
        :return: Boolean indicating availability
        """
        if not availabilities:
            return True

        # If availabilities is a single NurseAvailability object
        if hasattr(availabilities, "start_date") and hasattr(availabilities, "end_date"):
            return availabilities.start_date <= date <= availabilities.end_date

        # If availabilities is a list of NurseAvailability objects
        if isinstance(availabilities, list):
            return any(
                avail.start_date <= date <= avail.end_date
                for avail in availabilities
            )

        # If we can't determine the type, log a warning and assume available
        logger.warning(f"Unexpected type for availabilities: {type(availabilities)}")
        return True

    @staticmethod
    def get_schedule_week(date: datetime.date) -> int:
        """
        Determine the schedule week number for rotation purposes.

        We define week 1 as starting on the first day of the month.

        :param date: The date to check
        :return: Week number (1, 2, 3, 4, 5)
        """
        # Calculate days since start of month
        days_since_month_start = date.day - 1

        # Integer division by 7 gives us the week number (0-indexed)
        # Add 1 to make it 1-indexed
        return (days_since_month_start // 7) + 1

    @staticmethod
    def get_nurse_group(nurse: DepartmentMember) -> int:
        """
        Determine which rotation group a nurse belongs to based on their ID.

        Divides nurses into two equal groups (Group 1 and Group 2).

        :param nurse: The nurse to check
        :return: Group number (1 or 2)
        """
        # Convert UUID to integer for consistent group assignment
        uuid_int = int(nurse.user.id.hex, 16)
        return (uuid_int % 2) + 1

    @staticmethod
    def get_eligible_template_for_nurse(
        nurse: DepartmentMember,
        date: datetime.date,
        templates: list[ShiftTemplate]
    ) -> ShiftTemplate:
        """
        Determine which template a nurse should be assigned to based on.

        their group and the week number.

        Group 1 nurses get first template in odd weeks, second template in even weeks.
        Group 2 nurses get second template in odd weeks, first template in even weeks.

        :param nurse: The nurse to check
        :param date: The date of the shift
        :param templates: List of available templates
        :return: The appropriate template for this nurse on this date
        """
        if not templates:
            return None

        if len(templates) < 2:
            return templates[0]

        # Sort templates to ensure consistent assignment
        sorted_templates = sorted(templates, key=lambda t: t.id)
        first_template = sorted_templates[0]  # e.g., Morning
        second_template = sorted_templates[1]  # e.g., Night

        # Get week number (1-indexed) from start of month
        days_since_month_start = date.day - 1
        week_number = (days_since_month_start // 7) + 1

        # Get nurse group
        nurse_group = NurseEligibilityChecker.get_nurse_group(nurse)

        # Group 1: First template on odd weeks, Second template on even weeks
        # Group 2: Second template on odd weeks, First template on even weeks
        if week_number % 2 == 1:  # Odd week
            return first_template if nurse_group == 1 else second_template
        # Even week
        return second_template if nurse_group == 1 else first_template

    @staticmethod
    def check_shift_constraints(
        nurse: DepartmentMember,
        date: datetime.date,
        template: ShiftTemplate,
        context: SchedulerContext
    ) -> bool:
        """
        Comprehensive check for nurse shift eligibility with weekly rotation support.

        Ensures nurses stay on the same template for an entire week.
        """
        user_id = nurse.user.id
        nurse_avail = context.availabilities.get(user_id, [])
        nurse_state = context.shift_states.get(user_id)

        # Availability check
        if not NurseEligibilityChecker.is_nurse_available(nurse, date, nurse_avail):
            return False

        # Basic checks for overlapping shifts and role matching
        # ... existing checks ...

        # WEEKLY ROTATION: Get all templates for this date
        all_templates = list(
            ShiftTemplate.objects.filter(
                department=nurse.department
            ).order_by("id")[:2]  # Get the two primary templates
        )

        if not all_templates:
            return True

        # Check if this is the template this nurse should be on this week
        eligible_template = NurseEligibilityChecker.get_eligible_template_for_nurse(
            nurse, date, all_templates
        )

        if eligible_template and eligible_template.id != template.id:
            logger.info(
                f"Nurse {nurse.user.first_name} (Group {NurseEligibilityChecker.get_nurse_group(nurse)}) "
                f"should be on template '{eligible_template.name}', not '{template.name}'"
            )
            return False

        # Get the first day of this week (Monday)
        current_weekday = date.weekday()  # 0=Monday, 6=Sunday
        first_day_of_week = date - datetime.timedelta(days=current_weekday)

        # Check for weekly consistency - nurse should be on same template all week
        week_query = Q(
            user=nurse.user,
            start_datetime__date__gte=first_day_of_week,
            start_datetime__date__lt=first_day_of_week + datetime.timedelta(days=7)
        )

        weekly_shifts = GeneratedShift.objects.filter(week_query)

        if weekly_shifts.exists():
            # Nurse already has shifts this week, check template consistency
            existing_template_id = weekly_shifts.first().source_template.id
            if existing_template_id != template.id:
                # Nurse is already working a different template this week
                logger.info(
                    f"Nurse {nurse.user.first_name} already assigned to template #{existing_template_id} "
                    f"this week, cannot assign to template #{template.id}"
                )
                return False

        # Weekend policy check
        weekday_str = date.strftime("%a")
        is_weekend = weekday_str in ["Sat", "Sun"]
        if is_weekend and context.weekend_policy:
            weekend_count = getattr(nurse_state, "weekend_shift_count", 0)
            if weekend_count >= context.weekend_policy.max_weekend_shifts:
                return False

        return True
class ShiftAssignmentManager:
    """
    Manages the process of assigning shifts with improved error handling.
    """

    @classmethod
    def select_nurses_for_template(
        cls,
        nurses: list[DepartmentMember],
        context: SchedulerContext,
        date: datetime.date,
        template: ShiftTemplate,
        required_staff: int
    ) -> tuple[list[DepartmentMember], bool]:
        """
        Select eligible nurses for a shift template, respecting weekly rotation groups.
        """
        # Get all nurses who already have shifts on this date to avoid conflicts
        date_query = Q(start_datetime__date=date) | Q(
            start_datetime__date=date,
            end_datetime__date=date + datetime.timedelta(days=1)
        )

        nurses_with_shifts = set(
            GeneratedShift.objects.filter(date_query)
            .values_list("user_id", flat=True)
        )

        # Group all nurses by their rotation group
        # group1_nurses = []
        # group2_nurses = []

        # Get current week number (1-indexed) from start of month
        days_since_month_start = date.day - 1
        week_number = (days_since_month_start // 7) + 1

        # Get all templates in consistent order
        all_templates = list(
            ShiftTemplate.objects.filter(
                department=nurses[0].department if nurses else None
            ).order_by("id")[:2]  # Get the two primary templates
        )

        # If we don't have enough templates, return an empty list
        if len(all_templates) < 2 or template not in all_templates:
            return [], False

        # Determine which template index this is (0 or 1)
        template_index = all_templates.index(template)

        # Determine which group should be assigned to this template this week
        # Group 1: template[0] on odd weeks, template[1] on even weeks
        # Group 2: template[1] on odd weeks, template[0] on even weeks
        target_group = None
        if week_number % 2 == 1:  # Odd week
            target_group = 1 if template_index == 0 else 2
        else:  # Even week
            target_group = 2 if template_index == 0 else 1

        # Filter nurses by eligibility
        eligible_nurses = []
        for nurse in nurses:
            # Skip if nurse already has a shift on this date
            if nurse.user.id in nurses_with_shifts:
                continue

            # Get nurse's group
            nurse_group = NurseEligibilityChecker.get_nurse_group(nurse)

            # Check if this nurse should be in this template's group this week
            if nurse_group != target_group:
                continue

            # Final eligibility check
            if not NurseEligibilityChecker.check_shift_constraints(
                nurse, date, template, context
            ):
                continue

            # Add to eligible nurses list
            eligible_nurses.append(nurse)

        # Sort eligible nurses by preference if needed
        if context.user_preferences:
            # Sort nurses who prefer this template first
            preferred_nurses = []
            non_preferred_nurses = []

            for nurse in eligible_nurses:
                user_id = nurse.user.id
                preference = context.user_preferences.get(user_id)

                if (preference and preference.preferred_shift_types.exists() and
                    template in preference.preferred_shift_types.all()):
                    preferred_nurses.append(nurse)
                else:
                    non_preferred_nurses.append(nurse)

            eligible_nurses = preferred_nurses + non_preferred_nurses

        # Limit to required staff count
        selected_nurses = eligible_nurses[:required_staff]
        requirements_met = len(eligible_nurses) >= required_staff

        # Log detailed information
        day_type = "weekend" if date.strftime("%a") in ["Sat", "Sun"] else "weekday"
        logger.info(
            f"Template '{template.name}' on {date} ({day_type}): "
            f"Week {week_number}, Target Group: {target_group}, "
            f"Required staff: {required_staff}, "
            f"Selected: {len(selected_nurses)}, "
            f"Total eligible: {len(eligible_nurses)}"
        )

        return selected_nurses, requirements_met

    @classmethod
    def create_shifts_for_template(  # noqa: PLR0913
        cls,
        department: Department,
        nurses: list[DepartmentMember],
        context: SchedulerContext,
        date: datetime.date,
        template: ShiftTemplate,
        required_staff: int
    ) -> tuple[list[GeneratedShift], str | None]:
        """
        Create shifts for a specific template with improved error handling.
        """
        # CRITICAL FIX: Check if we already have shifts for this template and date
        # This prevents duplicate creation

        existing_shifts = GeneratedShift.objects.filter(
            department=department,
            source_template=template,
            start_datetime__date=date
        ).count()

        if existing_shifts > 0:
            logger.warning(
                f"Shifts already exist for template '{template.name}' on {date}. "
                f"Existing count: {existing_shifts}, Required: {required_staff}"
            )

            # If we already have enough shifts, skip creation
            if existing_shifts >= required_staff:
                logger.info(f"Skipping creation as {existing_shifts} shifts already exist")
                return [], None

            # Adjust required staff to account for existing shifts
            required_staff = required_staff - existing_shifts
            logger.info(f"Adjusted required staff to {required_staff}")

        # Select eligible nurses and check if requirements are met
        eligible_nurses, requirements_met = cls.select_nurses_for_template(
            nurses, context, date, template, required_staff
        )

        # Prepare error message if needed
        error_message = None
        day_type = "weekend" if date.strftime("%a") in ["Sat", "Sun"] else "weekday"

        if not requirements_met:
            error_message = (
                f"STAFFING SHORTAGE: On {date} ({day_type}), template '{template.name}' "
                f"requires {required_staff} staff but only {len(eligible_nurses)} eligible nurses found."
            )
            logger.warning(error_message)
            cls._notify_staffing_shortage(department, date, template,
                                          required_staff, len(eligible_nurses))
        else:
            logger.info(
                f"On {date}: Template '{template.name}' requires {required_staff} staff; "
                f"{len(eligible_nurses)} eligible found."
            )

        # Create shifts with available nurses
        created_shifts = []
        for nurse in eligible_nurses:
            # CRITICAL FIX: Double-check nurse doesn't already have a shift on this day
            # This is our final safety check
            has_shift = GeneratedShift.objects.filter(
                user=nurse.user,
                start_datetime__date=date
            ).exists()

            if has_shift:
                logger.warning(
                    f"Skipping shift creation for {nurse.user.first_name} on {date} - "
                    f"already has a shift on this day"
                )
                continue

            shift = cls.create_single_shift(
                nurse, department, date, template
            )
            if shift:
                created_shifts.append(shift)
                cls.update_nurse_state(nurse, context, date, template)

        return created_shifts, error_message

    @classmethod
    def _notify_staffing_shortage(
        cls,
        department: Department,
        date: datetime.date,
        template: ShiftTemplate,
        required_staff: int,
        available_staff: int
    ):
        """
        Send notification about staffing shortages.

        :param department: Department with shortage
        :param date: Date of shortage
        :param template: Shift template
        :param required_staff: Required staff count
        :param available_staff: Available staff count
        """
        # Implementation can vary based on your notification system
        # Example: Send email, push notification, or create a system alert

        day_type = "weekend" if date.strftime("%a") in ["Sat", "Sun"] else "weekday"
        shortage_amount = required_staff - available_staff

        # Example of notification content
        message = (
            f"URGENT: Staffing shortage for {department.name}\n"
            f"Date: {date} ({day_type})\n"
            f"Shift: {template.name} ({template.start_time}-{template.end_time})\n"
            f"Required staff: {required_staff}\n"
            f"Available staff: {available_staff}\n"
            f"Shortage: {shortage_amount} staff members\n\n"
            f"Please address this shortage as soon as possible."
        )

        logger.critical(message)

        # Add your notification logic here
        # For example:
        # send_email(department.head_email, "Staffing Shortage Alert", message)
        # create_system_notification(department.id, "staffing_shortage", message)

        # For now, just log the message
        return message

    @classmethod
    def create_single_shift(
        cls,
        nurse: DepartmentMember,
        department: Department,
        date: datetime.date,
        template: ShiftTemplate
    ) -> GeneratedShift | None:
        """
        Create a single shift for a nurse with timezone awareness.

        :param nurse: Nurse to assign shift to
        :param department: Department
        :param date: Date of shift
        :param template: Shift template
        :return: Created GeneratedShift or None
        """
        # Create naive datetime objects first
        naive_start_dt = datetime.datetime.combine(date, template.start_time)
        naive_end_dt = datetime.datetime.combine(date, template.end_time)

        # Handle overnight shifts
        if naive_end_dt <= naive_start_dt:
            naive_end_dt += datetime.timedelta(days=1)

        # Make the datetime objects timezone-aware using Django's timezone utilities
        start_dt = timezone.make_aware(naive_start_dt)
        end_dt = timezone.make_aware(naive_end_dt)

        # Log detailed information about shift creation
        logger.info(
            f"Creating shift for {nurse.user.first_name} on {date}: "
            f"{template.name} ({template.start_time}-{template.end_time})"
        )

        try:
            shift = GeneratedShift.objects.create(
                user=nurse.user,
                department=department,
                start_datetime=start_dt,
                end_datetime=end_dt,
                source_template=template,
                status=GeneratedShift.Status.SCHEDULED,
                penalty_score=0.0
            )
            return shift
        except DatabaseError as e:
            logger.exception(f"Failed to create shift for {nurse.user}: {e}")
            return None

    @classmethod
    def update_nurse_state(
        cls,
        nurse: DepartmentMember,
        context: SchedulerContext,
        date: datetime.date,
        template: ShiftTemplate
    ):
        """
        Update nurse's shift state after assignment, creating it if needed.

        :param nurse: Nurse to update
        :param context: Scheduling context
        :param date: Date of shift
        :param template: Shift template
        """
        user_id = nurse.user.id
        nurse_state = context.shift_states.get(user_id)

        # If nurse_state doesn't exist, create it
        if not nurse_state:
            # Import here to avoid circular imports
            from apps.scheduling.models import UserShiftState

            logger.info(f"Creating new shift state for nurse {nurse.user.first_name}")
            nurse_state = UserShiftState.objects.create(
                user=nurse.user,
                department=nurse.department,
                current_template=template,
                consecutive_weeks=1,
                last_shift_end=date,
                weekend_shift_count=1 if date.strftime("%a") in ["Sat", "Sun"] else 0
            )

            # Add the newly created state to the context
            context.shift_states[user_id] = nurse_state
        else:
            # Reset or increment consecutive weeks
            if nurse_state.current_template != template:
                nurse_state.consecutive_weeks = 1
                nurse_state.current_template = template
            else:
                nurse_state.consecutive_weeks += 1

            nurse_state.last_shift_end = date

            # Update weekend shift count
            if date.strftime("%a") in ["Sat", "Sun"]:
                nurse_state.weekend_shift_count = getattr(
                    nurse_state, "weekend_shift_count", 0
                ) + 1

            try:
                nurse_state.save()
                logger.info(
                    f"Updated shift state for {nurse.user.first_name}: "
                    f"Template: {template.name}, "
                    f"Consecutive weeks: {nurse_state.consecutive_weeks}, "
                    f"Weekend count: {getattr(nurse_state, 'weekend_shift_count', 0)}"
                )
            except DatabaseError as e:
                logger.exception(f"Failed to save nurse state for {nurse.user.first_name}: {e}")

        # Update the state in the context to ensure it's immediately available
        context.shift_states[user_id] = nurse_state

class ScheduleGenerator:
    """
    Updated schedule generator to assign weekly shift templates.
    """

    @classmethod
    def generate_weekly_schedule(cls, department_id: int, year: int, month: int):  # noqa: C901
        logger.info(f"Generating weekly schedule for department {department_id}, {year}-{month}")

        # Load department data as before
        try:
            data = load_department_data(department_id, datetime.date(year, month, 1))
        except (DatabaseError, ValueError, KeyError) as e:
            logger.critical(f"Failed to load department data: {e}")
            return

        context = SchedulerContext(
            availabilities=data["availabilities"],
            shift_states=data["shift_states"],
            user_preferences=data["user_preferences"],
            weekend_policy=data["weekend_policy"]
        )

        # Build a weekly calendar instead of a daily calendar.
        weekly_calendar = cls._build_weekly_calendar(year, month)

        # Assume the two primary templates are sorted (e.g., morning and night)
        primary_templates = sorted(
            [t for t in data["shift_templates"] if "morning" in t.name.lower() or "night" in t.name.lower()],
            key=lambda t: t.id
        )
        if len(primary_templates) < 2:
            logger.critical("Need at least two templates (morning and night) for rotation.")
            return

        # Define the primary and alternate templates
        primary_template = primary_templates[0]   # e.g., Morning
        alternate_template = primary_templates[1]   # e.g., Night

        # Divide nurses into two groups based on a consistent criterion (e.g., nurse ID)
        group1_nurses = []
        group2_nurses = []
        for nurse in data["active_members"]:
            uuid_int = int(nurse.user.id.hex, 16)
            if (uuid_int % 2) == 0:
                group1_nurses.append(nurse)
            else:
                group2_nurses.append(nurse)

        # Process each week in the monthly calendar
        for week in weekly_calendar:
            # Get week index (1-indexed)
            week_number = weekly_calendar.index(week) + 1

            # Decide assignment based on week parity
            if week_number % 2 == 1:
                group1_template = primary_template  # e.g., morning
                group2_template = alternate_template  # e.g., night
            else:
                group1_template = alternate_template
                group2_template = primary_template

            logger.info(f"Processing week {week_number}: "
                        f"Group 1 -> {group1_template.name}, "
                        f"Group 2 -> {group2_template.name}")

            # For each nurse in Group 1, assign the entire week with group1_template
            for nurse in group1_nurses:
                for date in week:
                    cls._create_shift_for_date(data["department"], nurse, context, date, group1_template)
                cls._update_nurse_state(nurse, context, week[-1], group1_template)

            # For each nurse in Group 2, assign the entire week with group2_template
            for nurse in group2_nurses:
                for date in week:
                    cls._create_shift_for_date(data["department"], nurse, context, date, group2_template)
                cls._update_nurse_state(nurse, context, week[-1], group2_template)

        logger.info("Weekly schedule generation complete.")

    @staticmethod
    def _build_weekly_calendar(year: int, month: int) -> list[list[datetime.date]]:
        """
        Build a weekly calendar with custom week boundaries.

        For example, if you want the week to start on Tuesday and end on Monday.
        Adjust this logic to meet your specific requirements.
        """
        # Create a list of all dates in the month
        import calendar
        days_in_month = calendar.monthrange(year, month)[1]
        all_dates = [datetime.date(year, month, day) for day in range(1, days_in_month + 1)]

        # Partition dates into weeks.
        # For this example, we assume a week starts on Tuesday.
        weeks = []
        current_week = []
        for date in all_dates:
            # Start a new week if it's Tuesday and we already have dates in the current week.
            if date.weekday() == 1 and current_week:
                weeks.append(current_week)
                current_week = [date]
            else:
                current_week.append(date)
        if current_week:
            weeks.append(current_week)
        return weeks

    @classmethod
    def _create_shift_for_date(cls, department, nurse, context, date, template):
        """
        Create a single shift for a nurse on a given date using the specified template.
        """
        # Check if nurse is available on this date
        nurse_avail = context.availabilities.get(nurse.user.id, [])
        if not NurseEligibilityChecker.is_nurse_available(nurse, date, nurse_avail):
            logger.info(f"Nurse {nurse.user.first_name} is not available on {date}")
            return None

        # Create timezone-aware datetime objects for the shift
        naive_start_dt = datetime.datetime.combine(date, template.start_time)
        naive_end_dt = datetime.datetime.combine(date, template.end_time)
        if naive_end_dt <= naive_start_dt:
            naive_end_dt += datetime.timedelta(days=1)
        start_dt = timezone.make_aware(naive_start_dt)
        end_dt = timezone.make_aware(naive_end_dt)

        try:
            shift = GeneratedShift.objects.create(
                user=nurse.user,
                department=department,
                start_datetime=start_dt,
                end_datetime=end_dt,
                source_template=template,
                status=GeneratedShift.Status.SCHEDULED,
                penalty_score=0.0
            )
            logger.info(f"Created shift for {nurse.user.first_name} on {date} using template {template.name}")
            return shift
        except DatabaseError as e:
            logger.exception(f"Failed to create shift for {nurse.user.first_name} on {date}: {e}")
            return None

    @classmethod
    def _update_nurse_state(cls, nurse, context, last_date: datetime.date, template):
        """
        Update nurse state after assignment for the week.

        Uses the last date of the week as the update reference.
        """
        user_id = nurse.user.id
        nurse_state = context.shift_states.get(user_id)
        if not nurse_state:
            from apps.scheduling.models import UserShiftState
            nurse_state = UserShiftState.objects.create(
                user=nurse.user,
                department=nurse.department,
                current_template=template,
                consecutive_weeks=1,
                last_shift_end=last_date,
                weekend_shift_count=1 if last_date.strftime("%a") in ["Sat", "Sun"] else 0
            )
            context.shift_states[user_id] = nurse_state
            logger.info(f"Created new state for {nurse.user.first_name}: Template {template.name}")
        else:
            # Reset or increment consecutive weeks based on whether the template changed
            if nurse_state.current_template != template:
                nurse_state.consecutive_weeks = 1
                nurse_state.current_template = template
            else:
                nurse_state.consecutive_weeks += 1
            nurse_state.last_shift_end = last_date
            if last_date.strftime("%a") in ["Sat", "Sun"]:
                nurse_state.weekend_shift_count = getattr(nurse_state, "weekend_shift_count", 0) + 1
            try:
                nurse_state.save()
                logger.info(f"Updated state for {nurse.user.first_name}: Template {template.name}, Consecutive Weeks {nurse_state.consecutive_weeks}")
            except DatabaseError as e:
                logger.exception(f"Failed to update state for {nurse.user.first_name}: {e}")
            context.shift_states[user_id] = nurse_state



def generate_monthly_schedule(department_id: int, year: int, month: int):
    """
    AConvenience function to generate a monthly schedule.

    :param department_id: Department ID
    :param year: Year of schedule
    :param month: Month of schedule
    """
    ScheduleGenerator.generate_weekly_schedule(department_id, year, month)
