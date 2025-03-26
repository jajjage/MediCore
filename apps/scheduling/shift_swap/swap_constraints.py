# we may use this constraint to check if the shifts belong to the same department before swapping them.
def can_swap_between_shifts(original_shift, proposed_shift):
    """
    Check additional constraints before a swap can occur.

    For example, you might check if the nurse s availability, role, or skill matches.
    """
    # Example: Ensure that both shifts belong to the same department.
    if original_shift.department != proposed_shift.department:
        return False, "Shifts belong to different departments."

    # Add additional checks as needed.
    return True, ""
