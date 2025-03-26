# shift_swap/swap_engine.py

import logging

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.scheduling.models import (  # adjust import paths as needed
    GeneratedShift,
    ShiftAssignmentHistory,
    ShiftSwapRequest,
)

from .swap_constraints import can_swap_between_shifts

logger = logging.getLogger(__name__)

def validate_swap_request(swap_request):
    """
    Validate that the swap request can be processed.

    This function checks that:
      - The original shift exists and is in SCHEDULED state.
      - (Optionally) the proposed shift is valid.
      - Additional constraints (e.g., nurse availability) can be checked here.
    """
    original_shift = swap_request.original_shift

    if original_shift.status != GeneratedShift.Status.SCHEDULED:
        raise ValidationError("Original shift must be in a scheduled state.")

    # (Optional) If a proposed shift is provided, you can check its constraints too.
    if swap_request.proposed_shift and swap_request.proposed_shift.status != GeneratedShift.Status.SCHEDULED:
            raise ValidationError("Proposed shift must be in a scheduled state.")

    # You could also add cross-checks such as ensuring that the requesting nurse is actually
    # assigned to the original shift, or that the requested nurse is available.
    return True

@transaction.atomic
def process_swap_request(swap_request):
    """
    Process a shift swap request. If approved, update the involved shifts and record history.

    This function assumes that validation has been done. It returns the updated swap request.
    """
    # Validate swap request first
    validate_swap_request(swap_request)

    original_shift = swap_request.original_shift
    proposed_shift = swap_request.proposed_shift  # This may be None if not pre-assigned.
    is_valid_swap, reason = can_swap_between_shifts(original_shift, proposed_shift)

    # Example: If swap is approved, update the swap status and modify the shifts accordingly.
    # (Your business logic may vary  for instance, you might switch the assignments between two nurses.)
    if swap_request.status == "APPROVED" and is_valid_swap:
        # Mark the original shift as swapped
        original_prev_state = original_shift.status
        original_shift.status = GeneratedShift.Status.SWAPPED
        original_shift.save()

        # If a proposed shift exists, update its status too
        if proposed_shift:
            proposed_prev_state = proposed_shift.status
            proposed_shift.status = GeneratedShift.Status.SWAPPED
            proposed_shift.save()

            # Optionally, update penalty scores or swap the user assignments if needed.
            # For example, you might swap the assigned users:
            temp = original_shift.user
            original_shift.user = proposed_shift.user
            proposed_shift.user = temp
            original_shift.save()
            proposed_shift.save()

            # Record the swap in history for both shifts
            ShiftAssignmentHistory.objects.create(
                shift_assignment=original_shift,
                previous_state=original_prev_state,
                new_state=original_shift.status,
                changed_by=swap_request.requesting_user,
                notes="Shift swap approved. User swapped with proposed shift."
            )
            ShiftAssignmentHistory.objects.create(
                shift_assignment=proposed_shift,
                previous_state=proposed_prev_state,
                new_state=proposed_shift.status,
                changed_by=swap_request.requesting_user,
                notes="Shift swap approved. User swapped with original shift."
            )
        else:
            # If there is no proposed shift, you might simply mark the original as swapped
            # and then later assign a new shift or notify the admin.
            ShiftAssignmentHistory.objects.create(
                shift_assignment=original_shift,
                previous_state=original_prev_state,
                new_state=original_shift.status,
                changed_by=swap_request.requesting_user,
                notes="Shift swap approved but no proposed shift provided."
            )

    # Update the swap request itself.
    swap_request.save()
    logger.info(f"Processed swap request {swap_request.id} with status {swap_request.status}")
    return swap_request
