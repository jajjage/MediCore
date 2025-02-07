import datetime
from datetime import timedelta

from django.db import models
from django.db.models import Case, F, IntegerField, Q, Sum, When
from django.db.models.functions import TruncWeek
from django.utils import timezone


class ShiftQuerySet(models.QuerySet):
    def for_user(self, user):
        return self.filter(user=user)

    def for_department(self, department):
        return self.filter(department=department)

    def upcoming(self):
        return self.filter(start_datetime__gte=timezone.now())

    def overlapping(self, start, end):
        return self.filter(
            models.Q(start_datetime__lt=end) &
            models.Q(end_datetime__gt=start)
        )

class ShiftManager(models.Manager):
    def get_queryset(self):
        return ShiftQuerySet(self.model, using=self._db)

    def create_from_template(self, template, date):
        return self.create(
            start_datetime=datetime.combine(date, template.start_time),
            end_datetime=datetime.combine(date, template.end_time),
            source_template=template
        )




class WorkloadManager(models.Manager):
    def weekly_summary(self, department, start_date):
        return self.filter(
            generated_shift__department=department,
            generated_shift__start_datetime__gte=start_date
        ).annotate(
            week=TruncWeek("generated_shift__start_datetime")
        ).values("week", "generated_shift__user").annotate(
            scheduled=Sum("scheduled_hours"),
            actual=Sum(F("actual_end") - F("actual_start")),
            overtime=Sum(Case(
                When(is_overtime=True, then=1),
                default=0,
                output_field=IntegerField()
            ))
        )
class DepartmentMemberShiftManager(models.Manager):
    def active_assignments(self, future_mode=False):
        now = timezone.now().date()

        return self.filter(
            department_member__is_active=True,
            shift_template__is_active=True,
            shift_template__valid_until__gte=now
        ).select_related("shift_template", "department_member")


