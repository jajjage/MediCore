from datetime import datetime

from .exceptions import BusinessLogicError


def date_validation(data):
     # Validate required fields
    if not data.get("end_date"):
        raise BusinessLogicError("End date is required", "END_DATE_REQUIRED")

    if not data.get("reason"):
        raise BusinessLogicError("Reason is required", "REASON_REQUIRED")

    # Parse and validate end date
    try:
        end_date = datetime.strptime(data["end_date"], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        raise BusinessLogicError("Invalid date format. Use YYYY-MM-DD", "INVALID_DATE_FORMAT")

    return end_date
