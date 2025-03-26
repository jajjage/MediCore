# constraints.py
from apps.scheduling.models import GeneratedShift, UserShiftHistory


class ConstraintChecker:
    def __init__(self, user, shift, context=None):
        self.user = user
        self.shift = shift
        self.context = context or {}

    def check_all(self):
        checks = [
            self.check_cooldown,
            self.check_consecutive,
            self.check_weekly_hours,
            self.check_shift_spacing,
            self.check_blackout_dates,
            self.check_qualifications
        ]

        return all(check() for check in checks)

    def check_cooldown(self):
        last_shift = UserShiftHistory.objects.filter(
            user=self.user,
            template=self.shift.template
        ).latest("end_datetime")

        return (self.shift.start_datetime - last_shift.end_datetime).days >= \
               self.shift.template.cooldown_days

    def check_shift_spacing(self):
        previous_shift = GeneratedShift.objects.filter(
            user=self.user,
            end_datetime__lt=self.shift.start_datetime
        ).latest("end_datetime")

        return (self.shift.start_datetime - previous_shift.end_datetime) >= \
               self.shift.template.min_shift_gap
