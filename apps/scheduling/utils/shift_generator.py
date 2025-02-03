# scheduling/utils/shift_generator.py
import logging
from datetime import date, datetime, timedelta
from types import SimpleNamespace

from dateutil import rrule
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_date

from apps.scheduling.models import DepartmentMemberShift, GeneratedShift, ShiftTemplate

logger = logging.getLogger(__name__)
class ShiftGenerator:
    def __init__(self, lookahead_weeks=2, force_future =False):
        self.lookahead = lookahead_weeks * 7
        self.generated_count = 0
        self.force_future = force_future

    def safe_date_convert(self, date_input):
        """Convert various date types to datetime.date."""
        if isinstance(date_input, datetime):
            return date_input.date()
        if isinstance(date_input, str):
            return parse_date(date_input).date()
        if isinstance(date_input, date):
            return date_input
        raise ValueError(f"Unsupported date type: {type(date_input)}")

    @transaction.atomic
    def generate_shifts(self, future_mode=False):
        print("sfwer3")
        assignments = DepartmentMemberShift.objects.active_assignments(future_mode)
        print(assignments)
        try:

            for assignment in assignments:
                # For future assignments, only generate first occurrence
                if future_mode:
                    self.process_assignment(
                        assignment,
                        max_generate=14  # Just seed initial shift
                    )
            self.process_assignment(assignment,  max_generate=14)
            return self.generated_count
        except Exception as e:
            print(f"Error generating shifts: {e!s}")
            raise
    def process_assignment(self, assignment, max_generate=None):
        dates = self.calculate_dates(assignment)
        existing = self.get_existing_shifts(assignment, dates)

        # Limit generations for future mode
        if max_generate:
            dates = dates[:max_generate]
        print(dates)
        for shift_date in dates:
            if date not in existing:
                self.create_shift(assignment, shift_date)
                self.generated_count += 1

    def combine_date_time(self, date_input, time_input):
        """Safely combine date and time inputs into timezone-aware datetime."""
        # Parse date
        print(date_input)
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
        print(date_obj, time_obj)
        naive_dt = datetime.combine(date_obj, time_obj)
        return timezone.make_aware(naive_dt)

    def calculate_dates(self, assignment):
        template = assignment.shift_template

        try:
            # Convert all dates to timezone-aware datetimes
            assignment_start = self.combine_date_time(
                assignment.assignment_start,
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

            # Calculate effective window
            effective_start = max(
                assignment_start,
                template_valid_from,
                timezone.localtime() - timedelta(days=7)  # 1 week buffer
            )

            effective_end = min(
                assignment_end or (timezone.localtime() + timedelta(days=self.lookahead)),
                template_valid_until or (timezone.localtime() + timedelta(days=self.lookahead))
            )

            # Generate dates
            dates = self.get_recurrence_dates(template, effective_start, effective_end)
            return dates

        except Exception as e:
            logger.exception(f"Calculation Error: {e!s}")
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

    def get_existing_shifts(self, assignment, dates):
        # Get existing shifts for these dates
        user = assignment.department_member.user
        department = assignment.shift_template.department

        existing = GeneratedShift.objects.filter(
            user=user,
            department=department,
            start_datetime__date__in=dates,
            source_template=assignment.shift_template
        ).values_list("start_datetime__date", flat=True)

        return set(existing)

    def create_shift(self, assignment, shift_dt):
        template = assignment.shift_template
        end_dt = shift_dt.replace(
            hour=template.end_time.hour,
            minute=template.end_time.minute
        )

        # Handle overnight shifts
        if template.end_time < template.start_time:
            end_dt += timedelta(days=1)

        GeneratedShift.objects.create(
            user=assignment.department_member.user,
            department=template.department,
            start_datetime=shift_dt,
            end_datetime=end_dt,
            source_template=template
        )

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
