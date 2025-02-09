# scheduling/utils/shift_generator.py
from __future__ import annotations

import calendar
import logging
import typing as t
from datetime import date as d
from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import NamedTuple

if t.TYPE_CHECKING:
    import uuid

from dateutil import rrule
from django.core.cache import cache
from django.db import transaction
from django.db.models import Count, Q
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

class GenerationContext(NamedTuple):
    initial_setup: bool
    generation_end_date: d | None
    new_shift_tracker: dict
    batch_days: int = 7
    ignore_now: bool = False
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
            grouped.setdefault(dept_id, {}).setdefault(user_id, []).append(assignment)
        return grouped

    def _process_department_assignments(
        self,
        department_id: uuid.UUID,
        user_assignments: dict[uuid.UUID, list],
        initial_setup: bool,  # noqa: FBT001
        generation_end_date: d | None
    ) -> int:
        """
        Process all assignments for a department, maintaining rotation for each user.
        """
        total_generated = 0
        department_new_shifts = {}
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
                context = GenerationContext(
                    initial_setup=initial_setup,
                    generation_end_date= generation_end_date,
                    new_shift_tracker=department_new_shifts
                )
                shifts_generated = self._generate_user_shifts(
                    sorted_assignments,
                    rotation_state,
                    context
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

    def _get_existing_shift_counts(self, template, candidate_dates: list[d]) -> dict:
        qs = GeneratedShift.objects.filter(
            source_template=template,
            department=template.department,
            start_datetime__date__in=candidate_dates
        ).values("start_datetime__date").annotate(count=Count("id"))
        return {item["start_datetime__date"]: item["count"] for item in qs}

    def _generate_user_shifts(
        self,
        assignments: list,
        rotation_state: UserShiftState,
        context: GenerationContext,
    ) -> int:
        """
        Generate shifts for a single doctor (user) while enforcing department-level staffing constraints.

        Args:
            assignments: List of shift assignments for the user
            rotation_state: Current rotation state for the user
            context: Dictionary containing:

        """
        shifts_generated = 0
        start_date, end_date = self._get_generation_window(context)
        current_block = start_date

        while current_block <= end_date:
            block_shifts = self._process_week_block(
                assignments,
                rotation_state,
                current_block,
                end_date,
                context
            )
            shifts_generated += block_shifts
            current_block += timedelta(days=7)

        if shifts_generated:
            self._update_rotation_state(rotation_state, end_date, assignments)

        return shifts_generated

    def _get_generation_window(self, context: GenerationContext) -> tuple[d, d]:
        """Determine the start and end dates for generation."""
        today = timezone.now().date()

        if context.initial_setup:
            start_date = self._next_monday(today)
            last_day = calendar.monthrange(start_date.year, start_date.month)[1]
            return start_date, d(start_date.year, start_date.month, last_day)

        start_date = today
        end_date = context.generation_end_date or (start_date + timedelta(days=context.batch_days))
        return start_date, end_date


    def _process_week_block(
        self,
        assignments: list,
        rotation_state: UserShiftState,
        block_start: d,
        generation_end: d,
        context: GenerationContext,
    ) -> int:
        """Process a single week block, returning number of shifts created."""
        block_end = min(block_start + timedelta(days=4), generation_end)
        template_used = False
        shifts_created = 0

        for i in range(len(assignments)):
            template_index = (rotation_state.rotation_index + i) % len(assignments)
            assignment = assignments[template_index]
            template = assignment.shift_template  # noqa: F841

            created = self._process_template_for_block(
                assignment,
                block_start,
                block_end,
                context
            )

            if created:
                shifts_created += created
                rotation_state.rotation_index = (template_index + 1) % len(assignments)
                template_used = True
                break

        if not template_used:
            rotation_state.rotation_index = (rotation_state.rotation_index + 1) % len(assignments)

        return shifts_created

    def _process_template_for_block(
        self,
        assignment: DepartmentMemberShift,
        block_start: d,
        block_end: d,
        context: GenerationContext,
    ) -> int:
        """Attempt to create shifts for a template in a block, returns number created."""
        template = assignment.shift_template
        candidate_dates = self._get_valid_dates_for_block(assignment, block_start, context)
        shifts_created = 0

        for date in candidate_dates:
            if not (block_start <= date <= block_end and date.weekday() <= WORK_WEEK_LAST_DAY):
                continue

            if self._can_create_shift(template, date, context.new_shift_tracker):
                self._create_shift(assignment, date)
                self._update_shift_tracker(template.id, date, context.new_shift_tracker)
                shifts_created += 1

        return shifts_created

    def _get_valid_dates_for_block(
        self,
        assignment: DepartmentMemberShift,
        block_start: d,
        context: GenerationContext,
    ) -> list[d]:
        """Get candidate dates for this template in the block."""
        datetimes = self.calculate_dates(
            assignment,
            next_start_date=block_start,
            ignore_now=context.ignore_now
        )
        return [dt.date() for dt in datetimes]

    def _can_create_shift(
        self,
        template: ShiftTemplate,
        date: d,
        new_shift_tracker: dict,
    ) -> bool:
        """Check if shift can be created considering max_staff constraints."""
        existing = GeneratedShift.objects.filter(
            source_template=template,
            department=template.department,
            start_datetime__date=date
        ).count()

        new_count = new_shift_tracker.get(template.id, {}).get(date, 0)
        return (existing + new_count) < template.max_staff

    def _update_shift_tracker(self, template_id: uuid, date: d, tracker: dict):
        """Update the shift creation tracker."""
        if template_id not in tracker:
            tracker[template_id] = {}
        tracker[template_id][date] = tracker[template_id].get(date, 0) + 1

    def _update_rotation_state(self, state: UserShiftState, end_date: d, assignments: list):
        """Update rotation state after generation."""
        template = assignments[state.rotation_index].shift_template
        state.last_shift_end = self.combine_date_time(end_date, template.end_time)
        state.save()

    def _next_monday(self, date_obj: d) -> d:
        """Get next Monday following the given date."""
        return date_obj + timedelta(days=(7 - date_obj.weekday()) % 7)

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

    def _create_shift(self, assignment, shift_date):
        """
        Create a shift for the given assignment on shift_date using the template's start and end times.

        Assumes shift_date is a date object.
        """
        template = assignment.shift_template
        start_dt = self.combine_date_time(shift_date, template.start_time)
        end_dt = self.combine_date_time(shift_date, template.end_time)
        # Adjust for overnight shifts.
        if template.end_time < template.start_time:
            end_dt += timedelta(days=1)
        GeneratedShift.objects.create(
            user=assignment.department_member.user,
            department=template.department,
            start_datetime=start_dt,
            end_datetime=end_dt,
            source_template=template
        )
        logger.info(f"Created shift: Start: {start_dt} - End: {end_dt} using template {template}.")


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
