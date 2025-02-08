# scheduling/utils/shift_generator.py
from __future__ import annotations

import calendar
import logging
import typing as t
from datetime import date, datetime, timedelta
from types import SimpleNamespace

if t.TYPE_CHECKING:
    import uuid

from dateutil import rrule
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_date

from apps.scheduling.models import (
    DepartmentMemberShift,
    GeneratedShift,
    ShiftTemplate,
    UserShiftState,
)

logger = logging.getLogger(__name__)
WORK_WEEK_LAST_DAY = 5  # Friday (0=Monday, 4=Friday, 5=Saturday, 6=Sunday)
class ShiftGenerator:
    def __init__(self, lookahead_weeks=4):
        self.lookahead = lookahead_weeks * 7
        self.generated_count = 0

    @transaction.atomic
    def generate_department_shifts(self, initial_setup=False, generation_end_date=None):
        """
        Generate shifts for all departments.

        Args:
            initial_setup: If True, generates full year of shifts.
            generation_end_date: Optional end date for generation window.

        """
        # Get all active department member shifts
        active_assignments = DepartmentMemberShift.objects.active_assignments()
        print(active_assignments)

        # Group assignments by department and user
        department_assignments = self._group_assignments(active_assignments)

        total_generated = 0
        try:
            for dept_id, user_assignments in department_assignments.items():
                total_generated += self._process_department_assignments(
                    dept_id,
                    user_assignments,
                    initial_setup,
                    generation_end_date
                )
        except Exception as e:
            logger.exception(
                "Failed to generate shifts for department %s: %s", dept_id, str(e)
            )

        return total_generated

    def _group_assignments(self, assignments) -> dict[uuid.UUID, dict[uuid.UUID, list]]:
        """
        Group assignments by department and user for efficient processing.

        Returns: {dept_id: {user_id: [assignments]}}
        """
        grouped = {}
        for assignment in assignments:
            dept_id = assignment.department_member.department_id
            user_id = assignment.department_member.user_id

            if dept_id not in grouped:
                grouped[dept_id] = {}
            if user_id not in grouped[dept_id]:
                grouped[dept_id][user_id] = []

            grouped[dept_id][user_id].append(assignment)

        return grouped

    def _process_department_assignments(
        self,
        department_id: uuid.UUID,
        user_assignments: dict[uuid.UUID, list],
        initial_setup: bool,  # noqa: FBT001
        generation_end_date: date | None
    ) -> int:
        """
        Process all assignments for a department, maintaining rotation for each user.
        """
        total_generated = 0

        # For initial setup, fetch the user_ids that already have a rotation state for this department.
        if initial_setup:
            existing_state_user_ids = set(
                UserShiftState.objects.filter(department_id=department_id)
                .values_list("user_id", flat=True)
            )
        else:
            existing_state_user_ids = set()  # Not used in daily generation

        user_ids = list(user_assignments.keys())
        try:
            for user_id in user_ids:
                print(f"Existing rotation State: {existing_state_user_ids} = from _process_department_assignments")
                # If initial_setup and a rotation state already exists for this user, skip them.
                if initial_setup and user_id in existing_state_user_ids:
                    continue

                assignments = user_assignments[user_id]
                # Sort assignments by template start time to establish rotation order.
                sorted_assignments = sorted(
                    assignments,
                    key=lambda x: x.shift_template.start_time
                )

                if initial_setup:
                    # For initial setup, create a new rotation state only for those without one.
                    rotation_state = self._create_initial_rotation_state(
                        user_id,
                        department_id,
                        sorted_assignments
                    )
                else:
                    # For daily generation, get or create the state.
                    rotation_state = self._get_rotation_state(
                        user_id,
                        department_id,
                        sorted_assignments
                    )

                # Generate shifts for this user.
                shifts_generated = self._generate_user_shifts(
                    sorted_assignments,
                    rotation_state,
                    initial_setup,
                    generation_end_date
                )
                total_generated += shifts_generated

        except Exception as e:
            logger.exception(
                f"Failed to generate shifts for user {user_id} in "
                f"department {department_id}: {e!s}"
            )

        return total_generated


    def _create_initial_rotation_state(
        self,
        user_id: uuid.UUID,
        department_id: uuid.UUID,
        assignments: list
    ) -> UserShiftState:
        """
        Create initial rotation state for a user during department setup.
        """
        # Find earliest assignment start date
        earliest_start = min(a.assignment_start for a in assignments)

        return UserShiftState.objects.create(
            user_id=user_id,
            department_id=department_id,
            current_template=assignments[0].shift_template,
            last_shift_end=timezone.make_aware(
                datetime.combine(earliest_start, datetime.min.time())
            ),
            rotation_index=0
        )


    def _get_rotation_state(
        self,
        user_id: uuid,
        department_id: uuid,
        assignments: list
    ) -> UserShiftState:
        """
        Get or create the rotation state for a user in a department.
        """
        try:
            return UserShiftState.objects.get(
                user_id=user_id,
                department_id=department_id
            )
        except UserShiftState.DoesNotExist:
            # Find the last generated shift for this user in this department
            last_shift = GeneratedShift.objects.filter(
                user_id=user_id,
                department_id=department_id
            ).order_by("-end_datetime").first()

            # Determine initial template and rotation index
            initial_template = assignments[0].shift_template
            initial_index = 0

            if last_shift:
                # Find the index of the last used template
                try:
                    initial_index = next(
                        i for i, a in enumerate(assignments)
                        if a.shift_template_id == last_shift.source_template_id
                    )
                    # Move to next template in rotation
                    initial_index = (initial_index + 1) % len(assignments)
                    initial_template = assignments[initial_index].shift_template
                except StopIteration:
                    pass

            return UserShiftState.objects.create(
                user_id=user_id,
                department_id=department_id,
                current_template=initial_template,
                last_shift_end=last_shift.end_datetime if last_shift else timezone.now(),
                rotation_index=initial_index
            )
    def _generate_user_shifts(
        self,
        assignments: list,
        rotation_state: UserShiftState,
        initial_setup: bool,           # True for initial (bulk) creation; False for daily/batch generation  # noqa: FBT001
        generation_end_date: date | None,
        batch_days: int = 7             # Used for daily generation if generation_end_date is not provided
    ) -> int:
        """
        Generate shifts for a single user using calculate_dates for recurrence.

        For initial_setup:
        - Determine a generation window starting from the next Monday (if today is not Monday)
            until the last day of the current month.
        - Divide that window into 7 day blocks.
        - For each block, use calculate_dates (with ignore_now=True) to get candidate dates.
        - For every candidate date within the block (i.e. every valid weekday),
            create a shift using the same shift template.
        - Advance the rotation state by one block (i.e. one template per block).
               For daily generation (initial_setup=False), a similar logic applies but on a shorter window.
        """
        shifts_generated = 0
        today = timezone.now().date()

        if initial_setup:
            # For initial setup, we want to schedule for the remainder of the current month.
            # If today is not Monday, start from the next Monday.
            if today.weekday() == 0:
                start_date = today
            else:
                days_until_monday = (7 - today.weekday())
                start_date = today + timedelta(days=days_until_monday)
            # End date is the last day of the current month.
            last_day = calendar.monthrange(start_date.year, start_date.month)[1]
            end_date = date(start_date.year, start_date.month, last_day)
            ignore_now = True
        else:
            # For daily/batch generation, use a shorter window.
            start_date = today
            end_date = generation_end_date if generation_end_date else (start_date + timedelta(days=batch_days))
            ignore_now = False

        # Process in blocks of 7 days (each block ideally covers 5 weekdays).
        block_count = 0  # number of blocks processed
        current_block_start = start_date

        while current_block_start <= end_date:
            # Define the current block: from current_block_start through 4 days later.
            # This block is meant to capture Monday through Friday.
            block_end = current_block_start + timedelta(days=4)
            block_end = min(block_end, end_date)

            # Determine which assignment (i.e. shift template) to use for this block.
            template_index = (rotation_state.rotation_index + block_count) % len(assignments)
            current_assignment = assignments[template_index]

            # Use calculate_dates to get candidate datetimes for the current assignment.
            candidate_datetimes = self.calculate_dates(
                current_assignment,
                next_start_date=current_block_start,
                ignore_now=ignore_now
            )
            # Convert candidate datetimes to dates.
            candidate_dates = [dt.date() for dt in candidate_datetimes]
            # Filter the candidate dates to those falling within this block.
            block_candidate_dates = [d for d in candidate_dates if current_block_start <= d <= block_end]
            # Optionally, enforce that they are weekdays (0=Mon, ..., 4=Fri):
            block_candidate_dates = [d for d in block_candidate_dates if d.weekday() < WORK_WEEK_LAST_DAY]

            # Instead of choosing just one date, iterate over all candidate dates in this block.
            for chosen_date in block_candidate_dates:
                # Check if a shift already exists for this candidate date.
                if chosen_date not in self._shift_exists(current_assignment, [chosen_date]):
                    self._create_shift(current_assignment, chosen_date)
                    shifts_generated += 1

            # Advance to the next block.
            block_count += 1
            current_block_start += timedelta(days=7)

        # Update rotation state after processing all blocks.
        rotation_state.rotation_index = (rotation_state.rotation_index + block_count) % len(assignments)
        # Update last_shift_end to reflect the end of the generation window.
        if shifts_generated:
            # For example, set last_shift_end using the end_date and the last used template.
            last_template_index = (rotation_state.rotation_index - 1) % len(assignments)
            last_assignment = assignments[last_template_index]
            rotation_state.last_shift_end = self._calculate_shift_end(last_assignment.shift_template, end_date)
        else:
            # Fallback in case no shift was created.
            last_template = assignments[(rotation_state.rotation_index - 1) % len(assignments)]
            rotation_state.last_shift_end = self.combine_date_time(end_date, last_template.shift_template.end_time)
        rotation_state.save()

        return shifts_generated


    def combine_date_time(self, date_input, time_input):
        """Safely combine date and time inputs into timezone-aware datetime."""
        # Parse date
        if isinstance(date_input, str):
            date_obj = parse_date(date_input)
        elif isinstance(date_input, datetime):
            date_obj = date_input.date()
        else:
            date_obj = date_input  # Assume it's already a date/datetime

        # Parse time
        if isinstance(time_input, str):
            time_obj = datetime.strptime(time_input, "%H:%M:%S").time()
        elif isinstance(time_input, datetime):
            time_obj = time_input.time()
        else:
            time_obj = time_input  # Assume it's already a time object

        # Create naive datetime then make aware
        naive_dt = datetime.combine(date_obj, time_obj)
        return timezone.make_aware(naive_dt)

    def calculate_dates(self, assignment, next_start_date=None, ignore_now=False):
        """
        Calculate all valid dates for a shift assignment, considering rotation.

        If ignore_now is True, the effective start date is computed solely based on the assignment and template dates,
        and does not force the start to be at or after timezone.localtime(). This is useful during initial setup.
        """
        template = assignment.shift_template
        try:
            # Create timezone-aware datetime objects
            assignment_start = self.combine_date_time(
                next_start_date or assignment.assignment_start,
                template.start_time
            )
            assignment_end = self.combine_date_time(
                assignment.assignment_end,
                template.end_time
            ) if assignment.assignment_end else None

            template_valid_from = self.combine_date_time(
                template.valid_from,
                template.start_time
            )
            template_valid_until = self.combine_date_time(
                template.valid_until,
                template.end_time
            ) if template.valid_until else None

            # When ignore_now is True, we do not force effective_start to be >= timezone.localtime()
            if ignore_now:
                effective_start = max(assignment_start, template_valid_from)
            else:
                effective_start = max(assignment_start, template_valid_from, timezone.localtime())

            effective_end = min(
                assignment_end or (timezone.localtime() + timedelta(days=self.lookahead)),
                template_valid_until or (timezone.localtime() + timedelta(days=self.lookahead))
            )

            dates = self.get_recurrence_dates(template, effective_start, effective_end)
            return dates

        except Exception as e:
            logger.exception(f"Date calculation error: {e}")
            return []

    def get_recurrence_dates(self, template, start_dt, end_dt):
        """Generate datetime objects for the recurrence rule."""
        try:
            rule = self.build_rrule(template, start_dt)
            return list(rule.between(start_dt, end_dt, inc=True))
        except Exception as e:
            logger.exception(f"Recurrence failed: {e!s}")
            return []

    def build_rrule(self, template, dtstart):
        """Create recurrence rule with proper datetime handling."""
        freq_map = {
            "DAILY": rrule.DAILY,
            "WEEKLY": rrule.WEEKLY,
            "MONTHLY": rrule.MONTHLY,
            "YEARLY": rrule.YEARLY
        }

        params = {
            "dtstart": dtstart,
            "freq": freq_map[template.recurrence],
            "interval": template.recurrence_parameters.get("interval", 1)
        }

        if template.recurrence_parameters.get("days"):
            params["byweekday"] = [
                self.parse_weekday(day)
                for day in template.recurrence_parameters["days"]
            ]

        return rrule.rrule(**params)

    def parse_weekday(self, day_str):
        weekday_map = {
            "MON": rrule.MO,
            "TUE": rrule.TU,
            "WED": rrule.WE,
            "THU": rrule.TH,
            "FRI": rrule.FR,
            "SAT": rrule.SA,
            "SUN": rrule.SU
        }
        return weekday_map[day_str.upper()]

    def _shift_exists(self, assignment, dates):
        # If 'dates' is not iterable (i.e., a single date), wrap it in a list.
        if not hasattr(dates, "__iter__") or isinstance(dates, (str, bytes)):
            dates = [dates]

        user = assignment.department_member.user
        department = assignment.shift_template.department

        existing = GeneratedShift.objects.filter(
            user=user,
            department=department,
            start_datetime__date__in=dates,
            source_template=assignment.shift_template
        ).values_list("start_datetime__date", flat=True)

        return set(existing)

    def _create_shift(self, assignment, shift_dt):
        """Create a new shift with proper datetime handling."""
        template = assignment.shift_template

        start_dt = self.combine_date_time(shift_dt, template.start_time)
        end_dt = self.combine_date_time(shift_dt, template.end_time)
        print(f"Start: {start_dt} - End: {end_dt} = from _create_shift")
        # Handle overnight shifts
        if template.end_time < template.start_time:
            end_dt += timedelta(days=1)

        GeneratedShift.objects.create(
            user=assignment.department_member.user,
            department=template.department,
            start_datetime=start_dt,
            end_datetime=end_dt,
            source_template=template
        )


    def _calculate_shift_end(self, template, shift_date):
        """Calculate the end datetime for a shift."""
        end_dt = self.combine_date_time(shift_date, template.end_time)

        # Handle overnight shifts
        if template.end_time < template.start_time:
            end_dt += timedelta(days=1)

        return end_dt

    # Validator helper
    def calculate_projected_hours_for_data(self, member, shift_data):
        """Calculate hours from raw serializer data."""
        total_hours = 0
        try:
            for shift in shift_data:
                # Create temporary assignment object with all required attributes
                temp_assignment = SimpleNamespace(
                    department_member=member,
                    shift_template=ShiftTemplate.objects.get(id=shift["shift_template"]),
                    assignment_start=shift.get("start_date", getattr(member, "start_date", None)),
                    assignment_end=shift.get("end_date", getattr(member, "end_date", None))
                )

                dates = self.calculate_dates(temp_assignment)

                # Safely get the shift template times
                template = temp_assignment.shift_template
                start_time = getattr(template, "start_time", datetime.min.time())
                end_time = getattr(template, "end_time", datetime.max.time())

                total_seconds = sum(
                    (datetime.combine(date, end_time) -
                    datetime.combine(date, start_time)).total_seconds()
                    for date in dates
                )
                total_hours += total_seconds / 3600

        except AttributeError as e:
            print(f"Error calculating hours: {e!s}")
            return 0

        return total_hours
