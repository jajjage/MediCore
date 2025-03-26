# shift_generator/calendar.py

import calendar
import datetime

WORK_WEEK_LAST_DAY = 5  # Friday (0=Monday, 4=Friday, 5=Saturday, 6=Sunday)
def build_month_calendar(year, month):
    """
    AReturns a list of dictionaries for each day in the given month.

    Each dictionary has:
      - date: a datetime.date object
      - day_type: "weekday" or "weekend"
    """
    days = []
    total_days = calendar.monthrange(year, month)[1]
    for day in range(1, total_days + 1):
        current_date = datetime.date(year, month, day)
        # Weekday numbers: Monday=0, Sunday=6
        day_type = "weekend" if current_date.weekday() >= WORK_WEEK_LAST_DAY else "weekday"
        days.append({
            "date": current_date,
            "day_type": day_type,
        })
    return days
