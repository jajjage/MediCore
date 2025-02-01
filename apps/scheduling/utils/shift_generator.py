# scheduling/utils/shift_generator.py
from datetime import datetime, timedelta

from dateutil import rrule
from django.db import transaction
from django.db.models import Q
from django.utils import timezone


class ShiftGenerator:
    def __init__(self, lookahead_weeks=2):
        self.lookahead = lookahead_weeks * 7
        self.generated_count = 0

    @transaction.atomic
    def generate_shifts(self):
        from apps.scheduling.models import DepartmentMemberShift, GeneratedShift

        # Get active assignments using custom queryset
        assignments = DepartmentMemberShift.objects.active_assignments()
        for assignment in assignments:
            self.process_assignment(assignment)

        return self.generated_count

    def process_assignment(self, assignment):
        dates = self.calculate_dates(assignment)
        existing_dates = self.get_existing_shifts(assignment, dates)

        for date in dates:
            if date not in existing_dates:
                self.create_shift(assignment, date)
                self.generated_count += 1

    def calculate_dates(self, assignment):
        start_date = max(
            assignment.assignment_start,
            timezone.now().date()
        )
        end_date = min(
            assignment.assignment_end or (timezone.now() + timedelta(weeks=4)).date(),
            (timezone.now() + timedelta(days=self.lookahead)).date()
        )

        return self.get_recurrence_dates(
            assignment.shift_template,
            start_date,
            end_date
        )

    def get_recurrence_dates(self, template, start, end):
        try:
            rule = self.build_rrule(template, start)
            return list(rule.between(start, end, inc=True))
        except (ValueError, TypeError, rrule.rrule.InvalidRRuleError) as e:
            # Handle invalid recurrence patterns
            print(f"Error generating dates for template {template.id}: {e!s}")
            return []

    def build_rrule(self, template, dtstart):
        freq_map = {
            "DAILY": rrule.DAILY,
            "WEEKLY": rrule.WEEKLY,
            "MONTHLY": rrule.MONTHLY,
            "YEARLY": rrule.YEARLY
        }

        params = {
            "dtstart": dtstart,
            "freq": freq_map[template.recurrence]
        }

        if template.recurrence_parameters.get("days"):
            params["byweekday"] = [
                self.parse_weekday(day)
                for day in template.recurrence_parameters["days"]
            ]

        if template.recurrence_parameters.get("interval"):
            params["interval"] = template.recurrence_parameters["interval"]

        return rrule.rrule(**params)

    def parse_weekday(self, day_str):
        # Convert string representation to dateutil weekday
        day_map = {
            "MON": rrule.MO,
            "TUE": rrule.TU,
            "WED": rrule.WE,
            "THU": rrule.TH,
            "FRI": rrule.FR,
            "SAT": rrule.SA,
            "SUN": rrule.SU
        }
        return day_map.get(day_str.upper(), rrule.MO)

    def get_existing_shifts(self, assignment, dates):
        # Get existing shifts for these dates
        from apps.scheduling.models import GeneratedShift
        user = assignment.department_member.user
        department = assignment.shift_template.department

        existing = GeneratedShift.objects.filter(
            user=user,
            department=department,
            start_datetime__date__in=dates,
            source_template=assignment.shift_template
        ).values_list("start_datetime__date", flat=True)

        return set(existing)

    def create_shift(self, assignment, date):
        from apps.scheduling.models import GeneratedShift
        template = assignment.shift_template

        # Handle overnight shifts
        if template.end_time < template.start_time:
            end_date = date + timedelta(days=1)
        else:
            end_date = date

        GeneratedShift.objects.create(
            user=assignment.department_member.user,
            department=template.department,
            start_datetime=datetime.combine(date, template.start_time),
            end_datetime=datetime.combine(end_date, template.end_time),
            source_template=template
        )

    # Validator helper
    def calculate_projected_hours(self, assignment):
        # Calculate total hours for the week
        dates = self.calculate_dates(assignment)
        total_seconds = sum(
            (datetime.combine(date, assignment.shift_template.end_time) -
             datetime.combine(date, assignment.shift_template.start_time)).total_seconds()
            for date in dates
        )
        return total_seconds / 3600
