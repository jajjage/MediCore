# filters.py
from datetime import datetime

import django_filters
from django.db.models import Q

from apps.scheduling.models import ShiftTemplate
from apps.staff.models.department_member import DepartmentMember


class ShiftTemplateFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr="icontains")
    department_name = django_filters.CharFilter(
        field_name="department__name",
        lookup_expr="icontains"
    )
    start_time_after = django_filters.TimeFilter(
        field_name="start_time",
        lookup_expr="gte"
    )
    start_time_before = django_filters.TimeFilter(
        field_name="start_time",
        lookup_expr="lte"
    )
    valid_from_after = django_filters.DateFilter(
        field_name="valid_from",
        lookup_expr="gte"
    )
    valid_until_before = django_filters.DateFilter(
        field_name="valid_until",
        lookup_expr="lte"
    )
    is_currently_valid = django_filters.BooleanFilter(method="filter_currently_valid")
    role_requirements = django_filters.TypedChoiceFilter(
        field_name="role_requirement",
        choices=DepartmentMember.ROLE_TYPES
    )
    min_max_staff = django_filters.NumberFilter(
        field_name="max_staff",
        lookup_expr="gte"
    )
    max_max_staff = django_filters.NumberFilter(
        field_name="max_staff",
        lookup_expr="lte"
    )
    recurrence_type = django_filters.TypedChoiceFilter(
        field_name="recurrence",
        choices=ShiftTemplate.Recurrence.choices
    )
    has_recurrence_parameters = django_filters.BooleanFilter(
        method="filter_has_recurrence_parameters"
    )

    def filter_currently_valid(self, queryset, name, value):
        from django.utils import timezone
        today = timezone.now().date()
        if value:
            return queryset.filter(
                Q(valid_from__lte=today) &
                (Q(valid_until__gte=today) | Q(valid_until__isnull=True))
            )
        return queryset.filter(
            Q(valid_from__gt=today) |
            Q(valid_until__lt=today)
        )

    def filter_has_recurrence_parameters(self, queryset, name, value):
        if value:
            return queryset.exclude(recurrence_parameters={})
        return queryset.filter(recurrence_parameters={})

    class Meta:
        model = ShiftTemplate
        fields = {
            "department": ["exact"],
            "is_active": ["exact"],
        }
