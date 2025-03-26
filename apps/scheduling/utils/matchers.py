# matchers.py

from django.contrib.auth import get_user_model

from apps.scheduling.models import UserAvailability

from .constraints import ConstraintChecker

User = get_user_model()
class SwapMatcher:
    def __init__(self, swap_request):
        self.swap = swap_request
        self.original_shift = swap_request.original_shift

    def find_matches(self):
        base_query = User.objects.filter(
            qualifications=self.original_shift.template,
            is_active=True
        ).exclude(pk=self.swap.requesting_user.pk)

        return [
            user for user in base_query
            if self._is_available(user) and
            self._passes_constraints(user)
        ]

    def _is_available(self, user):
        return not UserAvailability.objects.filter(
            user=user,
            start_date__lte=self.original_shift.start_datetime,
            end_date__gte=self.original_shift.end_datetime
        ).exists()

    def _passes_constraints(self, user):
        return ConstraintChecker(
            user=user,
            shift=self.original_shift,
            context={"swap_mode": True}
        ).check_all()
