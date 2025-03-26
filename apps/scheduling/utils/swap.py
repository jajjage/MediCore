# matchers.py

from __future__ import annotations

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from apps.scheduling.models import ShiftSwapRequest, UserAvailability, UserShiftState

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

class SwapValidator:
    def __init__(self, swap_request):
        self.swap = swap_request
        self.original_shift = swap_request.original_shift
        self.requesting_user = swap_request.requesting_user
        self.requested_user = swap_request.requested_user

    def validate_swap(self):
        return (
            self._validate_users() and
            self._validate_timing() and
            self._validate_constraints() and
            self._validate_qualifications()
        )

    def _validate_users(self):
        return self.requesting_user != self.requested_user

    def _validate_timing(self):
        now = timezone.now()
        return (
            self.original_shift.start_datetime > now + timedelta(hours=4) and
            self.swap.expiration > now
        )

    def _validate_constraints(self):
        return ConstraintChecker(
            user=self.requested_user,
            shift=self.original_shift
        ).check_all()

    def _validate_qualifications(self):
        return self.original_shift.template in self.requested_user.qualifications.all()

class SwapProcessor:
    @transaction.atomic
    def process_pending_swaps(self) -> dict[str, int]:
        stats = {"processed": 0, "violations": 0}
        pending_swaps = ShiftSwapRequest.objects.filter(
            status="pending",
            expiration__gt=timezone.now()
        ).select_related("original_shift", "requesting_user", "requested_user")

        for swap in pending_swaps:
            if self._validate_and_execute(swap):
                stats["processed"] += 1
            else:
                stats["violations"] += 1

        return stats

    def _validate_and_execute(self, swap: ShiftSwapRequest) -> bool:
        validator = SwapValidator(swap)
        if not validator.validate():
            swap.status = "rejected"
            swap.save()
            return False

        checker = ConstraintChecker(
            user=swap.requested_user,
            shift=swap.original_shift,
            context={"is_swap": True}
        )

        if not checker.validate():
            swap.status = "rejected"
            swap.save()
            return False

        self._execute_swap(swap)
        return True

    def _execute_swap(self, swap: ShiftSwapRequest):
        original = swap.original_shift
        original.user = swap.requested_user
        original.save()

        swap.status = "approved"
        swap.save()

        UserShiftState.objects.update_cooldowns(
            user=swap.requested_user,
            template=original.source_template
        )


class SwapUtils:
    @staticmethod
    def create_swap_request(original_shift, proposed_shift, requesting_user, reason):
        expiration = timezone.now() + timedelta(days=1)
        return ShiftSwapRequest.objects.create(
            original_shift=original_shift,
            proposed_shift=proposed_shift,
            requesting_user=requesting_user,
            requested_user=proposed_shift.user,
            reason=reason,
            expiration=expiration
        )

    @staticmethod
    def cancel_swap_request(swap_request):
        swap_request.status = "rejected"
        swap_request.save()

    @staticmethod
    def approve_swap_request(swap_request):
        swap_request.status = "approved"
        swap_request.save()

    @staticmethod
    def reject_swap_request(swap_request):
        swap_request.status = "rejected"
        swap_request.save()

    @staticmethod
    def expire_swap_requests():
        now = timezone.now()
        expired_swaps = ShiftSwapRequest.objects.filter(
            status="pending",
            expiration__lt=now
        )

        for swap in expired_swaps:
            swap.status = "rejected"
            swap.save()

class ConstraintViolationError(Exception):
    pass
