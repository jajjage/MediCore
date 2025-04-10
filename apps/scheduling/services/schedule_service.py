#Staff scheduling and appointent service

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from enum import Enum
from typing import Any, TypeAlias

from dateutil.relativedelta import relativedelta
from django.apps import apps
from django.core.cache import cache
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.scheduling.models import GeneratedShift
from apps.staff.models.staff_profile import DoctorProfile

# Type Aliases for better type hinting
DateTimeRange: TypeAlias = tuple[datetime, datetime]
ValidationResult: TypeAlias = dict[str, bool | str]

class AppointmentStatus(Enum):
    PENDING = "pending"
    CONFIRMED = "approved"
    CANCELED = "canceled"
    COMPLETED = "completed"
    RESCHEDULED = "rescheduled"
    NO_SHOW = "no_show"

class RecurrencePattern(Enum):
    DAILY = "Daily"
    WEEKLY = "Weekly"
    BIWEEKLY = "Biweekly"
    MONTHLY = "Monthly"
    CUSTOM = "Custom"

@dataclass
class TimeSlot:
    start_time: datetime
    end_time: datetime
    is_available: bool
    conflict_type: str | None = None
    conflict_id: str | None = None

class AppointmentTimeConflictError(Exception):
    """ACustom exception for appointment time conflicts."""

    def __init__(self, message: str, conflicting_appointment=None):
        self.message = message
        self.conflicting_appointment = conflicting_appointment
        super().__init__(self.message)

class SchedulePatternService:
    """Service for managing physician schedule patterns."""

    @classmethod
    def get_schedule_pattern(cls, physician_id: str, week_start: date, department_id: str | None = None) -> dict:
        """Get schedule pattern for a physician."""
        # Get current week boundaries
        week_start = week_start - timezone.timedelta(days=week_start.weekday())
        print(week_start)
        cache_key = cls._build_cache_key(physician_id, department_id, week_start)

        # Try cache first
        if (cached := cache.get(cache_key)) is not None:
            print(f"cached {cached}")
            return cached

        # Cache miss - generate fresh data
        schedule = cls._generate_schedule(physician_id, department_id, week_start)
        print(f"frh {schedule}")
        legacy_format = cls._convert_to_legacy_format(schedule)

        # Cache with timeout and versioning
        cache.set(
            cache_key,
            legacy_format,
            timeout=3600  # 1 hour - balances freshness and performance
        )
        return legacy_format


    @staticmethod
    def _build_cache_key(physician_id: str, department_id: str | None, week_start: date) -> str:
        base_key = f"schedule_v2:{physician_id}:{week_start.isoformat()}"
        return f"{base_key}:{department_id}" if department_id else f"{base_key}:all"

    @classmethod
    def _generate_schedule(cls, physician_id: str, department_id: str | None, week_start: date) -> dict:
        week_end = week_start + timezone.timedelta(days=6)
        print(week_end)
        print(physician_id, department_id)
         # Get relevant shifts for this week
        shifts = GeneratedShift.objects.filter(
            user_id=physician_id,
            start_datetime__date__gte=week_start,
            end_datetime__date__lte=week_end,
            status="SCHEDULED"
        ).select_related("department").order_by("start_datetime")

        if department_id:
            shifts = shifts.filter(department_id=department_id)
        print(shifts)

        # Aggregate shifts by weekday
        schedule = defaultdict(list)
        for shift in shifts:
            day = shift.start_datetime.strftime("%A").lower()
            schedule[day].append({
                "start": shift.start_datetime.time().strftime("%H:%M"),
                "end": shift.end_datetime.time().strftime("%H:%M"),
                "location": shift.department.name,
                "shift_type": shift.source_template.name if shift.source_template else "Custom"
            })
        return schedule

    @classmethod
    def invalidate_cache(cls, physician_id: str, week_start: date, department_id: str | None = None):
        """Call this when shifts change for a physician."""
        week_start = week_start - timezone.timedelta(days=week_start.weekday())
        cache_key = cls._build_cache_key(physician_id, department_id, week_start)
        cache.delete(cache_key)

    @staticmethod
    def _convert_to_legacy_format(shifts: dict) -> dict:
        """Convert dynamic shifts to legacy schedule pattern format."""
        # In _convert_to_legacy_format
        legacy_format = {}
        days_of_week = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

        for day in days_of_week:
            # Check if the day exists in shifts and is non-empty
            if shifts.get(day):
                # If any shift for the day is emergency, you might want to set max_appointments to 0.
                if any(s["shift_type"] == "EMERGENCY" for s in shifts[day]):
                    # If you wish to block appointments when emergency shifts are present
                    legacy_format[day] = {"max_appointments": 0}
                # Otherwise, take the first shift for legacy compatibility.
                primary_shift = shifts[day][0]
                legacy_format[day] = {
                    "start": primary_shift["start"],
                    "end": primary_shift["end"],
                    "max_appointments": SchedulePatternService._calculate_max_appointments(
                        primary_shift["start"],
                        primary_shift["end"],
                        slot_duration=30  # You might retrieve this value from your department config
                    ),
                    "slot_duration": 30
                }
            else:
                # For days that are missing or have an empty list, set the value to None.
                legacy_format[day] = None

        return legacy_format


    @staticmethod
    def _calculate_max_appointments(start: str, end: str, slot_duration: int) -> int:
        """Calculate appointments based on shift duration."""
        start_time = datetime.strptime(start, "%H:%M").time()
        end_time = datetime.strptime(end, "%H:%M").time()
        duration = datetime.combine(timezone.now().date(), end_time) - datetime.combine(timezone.now().date(), start_time)
        return int(duration.total_seconds() // 60 // slot_duration)

    @staticmethod
    def validate_schedule_pattern(pattern: dict) -> ValidationResult:  # noqa: ARG004
        """No longer needed for dynamic schedules, but kept for API compatibility."""
        return {"valid": True, "message": "Dynamic schedules require shift validation instead"}



class RecurringAppointmentService:
    RECURRENCE_CALCULATORS = {
        RecurrencePattern.DAILY: lambda start_date: start_date + timedelta(days=1),
        RecurrencePattern.WEEKLY: lambda start_date: start_date + timedelta(weeks=1),
        RecurrencePattern.BIWEEKLY: lambda start_date: start_date + timedelta(weeks=2),
        RecurrencePattern.MONTHLY: lambda start_date: start_date + relativedelta(months=1)
    }

    @classmethod
    def generate_recurring_dates(
        cls,
        start_date: date,
        start_time: time,
        pattern: RecurrencePattern,
        occurrences: int,
        excluded_dates: set[date] | None = None
    ) -> list[datetime]:
        """
        Generate dates for recurring appointments.

        Args:
            start_date: Initial appointment date
            start_time: Appointment time
            pattern: 'Daily', 'Weekly', or 'Monthly'
            occurrences: number
            excluded_dates: Number of appointments to generate

        Returns:
            List of datetime objects for the recurring appointments

        """
        if pattern not in RecurrencePattern:
            raise ValueError(f"Invalid recurrence pattern: {pattern}")

        excluded_dates = excluded_dates or set()
        dates = []
        current_date = start_date
        attempts = 0
        max_attempts = occurrences * 2  # Prevent infinite loops

        while len(dates) < occurrences and attempts < max_attempts:
            if current_date not in excluded_dates:
                dates.append(timezone.datetime.combine(current_date, start_time))

            current_date = cls.RECURRENCE_CALCULATORS[pattern](current_date)
            attempts += 1

        return dates

    @classmethod
    def create_recurring_appointments(
        cls,
        serializer: Any,
        staff_member: Any,
        patient_id: str,
        occurrences: int = 3,
        excluded_dates: set[date] | None = None
    ) -> list[any]:
        """
        Create a series of recurring appointments.

        Args:
            serializer: Validated appointment serializer
            staff_member: Staff member creating appointments
            patient_id: Patient ID
            occurrences: Number of appointments to create
            excluded_dates: Excluded date

        Returns:
            List of created appointments

        Raises:
            AppointmentTimeConflict: If any appointment time is invalid

        """
        dates = cls.generate_recurring_dates(
            start_date=serializer.validated_data["appointment_date"],
            start_time=serializer.validated_data["appointment_time"],
            pattern=RecurrencePattern(serializer.validated_data["recurrence_pattern"]),
            occurrences=occurrences,
            excluded_dates=excluded_dates
        )

        # Validate all dates first
        cls._validate_recurring_dates(dates, serializer, staff_member)

        # Create appointments
        return cls._create_appointments(dates, serializer, staff_member, patient_id)

    @staticmethod
    def _validate_recurring_dates(
        dates: list[str | datetime],  # Accept either strings or datetime objects
        serializer: Any,
        staff_member: Any  # noqa: ARG004
    ) -> None:
        """Validate availability for all recurring dates."""
        for appointment_date in dates:
            # Handle string dates
            if isinstance(appointment_date, str):
                try:
                    appointment_datetime = datetime.fromisoformat(appointment_date)
                except ValueError as e:
                    raise ValidationError(f"Invalid date format: {appointment_date}") from e
            else:
                appointment_datetime = appointment_date

            result = AppointmentService.check_availability(
                physician_id=serializer.validated_data["user"].id,
                start_datetime=appointment_datetime,
                end_datetime=appointment_datetime + timedelta(
                    minutes=serializer.validated_data.get("duration_minutes", 30)
                )
            )


            if not result["available"]:
                raise AppointmentTimeConflictError(
                    f"Physician not available at {appointment_datetime}: {result['message']}"
                )

    @staticmethod
    def _create_appointments(
        dates: list[datetime],
        serializer: Any,
        staff_member: Any,
        patient_id: str
    ) -> list[Any]:
        """Create all appointments in the series."""
        PatientAppointment = apps.get_model("patients", "PatientAppointment")
        created_appointments = []

        with transaction.atomic():
            for appointment_datetime in dates:
                appointment_data = {
                    **serializer.validated_data,
                    "appointment_date": appointment_datetime.date(),
                    "appointment_time": appointment_datetime.time(),
                    "is_recurring": True,
                    "patient_id": patient_id,
                    "created_by": staff_member,
                    "modified_by": staff_member,
                    "status": AppointmentStatus.PENDING.value
                }

                appointment = PatientAppointment.objects.create(**appointment_data)
                created_appointments.append(appointment)

        return created_appointments[0]


class AppointmentTimeService:
    """Handles appointment time calculations and validations."""

    @staticmethod
    def calculate_end_time(start_time: datetime, duration: int) -> datetime:
        """Calculate appointment end time based on duration."""
        return start_time + timedelta(minutes=duration)

    @staticmethod
    def is_within_schedule(schedule: dict, check_datetime: datetime) -> bool:
        """Check if time falls within schedule."""
        day_name = check_datetime.strftime("%A").lower()
        day_schedule = schedule.get(day_name)

        if not day_schedule:
            raise AppointmentTimeConflictError(f"Appointment are not allow on {day_name.title()}")

        check_time = check_datetime.time()
        start_time = timezone.make_aware(datetime.strptime(day_schedule["start"], "%H:%M")).time()
        end_time = timezone.make_aware(datetime.strptime(day_schedule["end"], "%H:%M")).time()

        # Handle schedule crossing midnight
        if (end_time < start_time and (check_time >= start_time or check_time <= end_time )) or (start_time <= check_time <= end_time):
            return True
        raise AppointmentTimeConflictError(
            f"Appointment on {day_name.title()} must be between {day_schedule['start']} and {day_schedule['end']}. ")

    @staticmethod
    def get_available_slots(
        physician_id: str,
        target_date: date,
        department_id: str | None = None,
        duration: int = 30
    ) -> list[TimeSlot]:
        """Get available appointment slots for a specific date."""
        schedule = SchedulePatternService.get_schedule_pattern(physician_id, department_id)
        day_schedule = schedule.get(target_date.strftime("%A").lower())

        if not day_schedule:
            return []

        # Generate time slots
        slots = []
        start_time = datetime.combine(
            target_date,
            datetime.strptime(day_schedule["start"], "%H:%M%z").time()
        )
        end_time = datetime.combine(
            target_date,
            datetime.strptime(day_schedule["end"], "%H:%M%z").time()
        )

        while start_time < end_time:
            slot_end = start_time + timedelta(minutes=duration)
            if slot_end > end_time:
                break

            is_available = AppointmentService.check_availability(
                physician_id, start_time, slot_end
            )["available"]

            slots.append(TimeSlot(
                start_time=start_time,
                end_time=slot_end,
                is_available=is_available
            ))

            start_time = slot_end

        return slots

class AppointmentService:
    """Main service for appointment management."""

    @staticmethod
    @transaction.atomic
    def create_appointment(
        serializer: Any,
        department: Any,
        physician: Any,
        staff_member: Any,
        patient_id: str,
    ) -> Any:
        """Create a single or recurring appointment."""
         # Check schedule pattern
        if serializer.validated_data["is_recurring"]:
            return RecurringAppointmentService.create_recurring_appointments(
                serializer, staff_member, patient_id
            )
        AppointmentService._validate_creation(
            patient_id,
            serializer.validated_data["appointment_date"],
            serializer.validated_data["appointment_time"]
        )

        return serializer.save(
            patient_id=patient_id,
            physician=physician,
            department=department,
            created_by=staff_member,
            modified_by=staff_member,
            status=AppointmentStatus.PENDING.value
        )

    @staticmethod
    @transaction.atomic
    def update_appointment(
        appointment_id: str,
        serializer: Any,
        staff_member: Any
    ) -> Any:
        """Update an existing appointment."""
        PatientAppointment = apps.get_model("patients", "PatientAppointment")
        appointment = PatientAppointment.objects.get(id=appointment_id)

        if appointment.status == AppointmentStatus.CANCELED.value:
            raise ValidationError({"message": "Cannot update canceled appointment"})

        # Check availability if time is being changed
        if (serializer.validated_data.get("appointment_date") != appointment.appointment_date or
            serializer.validated_data.get("appointment_time") != appointment.appointment_time):
            availability = AppointmentService.check_availability(
                physician_id=appointment.physician_id,
                start_datetime=datetime.combine(
                    serializer.validated_data["appointment_date"],
                    serializer.validated_data["appointment_time"]
                ),
                end_datetime=datetime.combine(
                    serializer.validated_data["appointment_date"],
                    serializer.validated_data["appointment_time"]
                ) + timedelta(minutes=serializer.validated_data.get("duration_minutes", 30)),
                exclude_appointment_id=appointment_id
            )
            if not availability["available"]:
                raise AppointmentTimeConflictError(availability["message"])

        return serializer.save(modified_by=staff_member)

    @staticmethod
    def check_availability(
        physician_id: str,
        start_datetime: datetime,
        end_datetime: datetime,
        exclude_appointment_id: str | None = None,
        department_id: str | None = None
    ) -> dict:
        """Check physician availability for a time range."""
        try:
            physician = DoctorProfile.objects.select_related(
                "user"
                ).get(
                user_id=physician_id
            )
            filter_role = physician.user.hospital_memberships_user.first().role.name
            if department_id and filter_role != "Doctor" and not physician.user.department_members.filter(
                department_id=department_id,
                department_type="CLINICAL"
            ).exists():
                return {
                    "available": False,
                    "message": "Physician not assigned to specified department"
                }

            # Check schedule pattern
            schedule = SchedulePatternService.get_schedule_pattern(
                physician_id, department_id
            )

            if not AppointmentTimeService.is_within_schedule(schedule, start_datetime):
                return {
                    "available": False,
                    "message": "Time outside physician's working hours"
                }

            # Check existing appointments
            overlap_query = Q(
                physician_id=physician_id,
                status__in=[
                    AppointmentStatus.PENDING.value,
                    AppointmentStatus.CONFIRMED.value
                ],
                appointment_date=start_datetime,
                appointment_time__lt=end_datetime,
                end_time__gt=start_datetime
            )

            if exclude_appointment_id:
                overlap_query &= ~Q(id=exclude_appointment_id)

            PatientAppointment = apps.get_model("patients", "PatientAppointment")
            if PatientAppointment.objects.filter(overlap_query).exists():
                return {
                    "available": False,
                    "message": "Time conflicts with existing appointment"
                }

            return {
                "available": True,
                "message": "Physician is available"
            }

        except DoctorProfile.DoesNotExist:
            return {
                "available": False,
                "message": "Physician not found or inactive"
            }

    @staticmethod
    def _validate_creation(
        patient_id: str,
        appointment_date: date,
        appointment_time: time
    ) -> None:
        """Validate appointment creation prerequisites."""
        PatientAppointment = apps.get_model("patients", "PatientAppointment")
        validation_result = PatientAppointment.can_create_appointment(
            patient_id=patient_id,
            appointment_date=appointment_date,
            appointment_time=appointment_time
        )

        if not validation_result["allowed"]:
            raise ValidationError(validation_result["message"])

    @staticmethod
    def cancel_appointment(
        appointment_id: str,
        staff_member: Any,
        cancellation_reason: str
    ) -> Any:
        """Cancel an existing appointment with reason."""
        PatientAppointment = apps.get_model("patients", "PatientAppointment")
        appointment = PatientAppointment.objects.get(id=appointment_id)

        if appointment.status == AppointmentStatus.COMPLETED.value:
            raise ValidationError("Cannot cancel completed appointment")

        if appointment.status == AppointmentStatus.CANCELED.value:
            raise ValidationError("Appointment is already cancelled")

        appointment.status = AppointmentStatus.CANCELED.value
        appointment.cancellation_reason = cancellation_reason
        appointment.canceled_by = staff_member
        appointment.canceled_at = timezone.now()
        appointment.modified_by = staff_member
        appointment.save()

        return appointment

    @staticmethod
    def reschedule_appointment(
        appointment_id: str,
        new_date: date,
        new_time: time,
        staff_member: Any,
        reschedule_reason: str
    ) -> Any:
        """Reschedule an existing appointment."""
        PatientAppointment = apps.get_model("patients", "PatientAppointment")
        appointment = PatientAppointment.objects.get(id=appointment_id)

        if appointment.status in [AppointmentStatus.COMPLETED.value,
                                AppointmentStatus.CANCELED.value]:
            raise ValidationError(f"Cannot reschedule {appointment.status} appointment")

        # Check availability for new time
        new_start = datetime.combine(new_date, new_time)
        new_end = new_start + timedelta(minutes=appointment.duration_minutes)

        availability = AppointmentService.check_availability(
            physician_id=appointment.physician_id,
            start_datetime=new_start,
            end_datetime=new_end,
            exclude_appointment_id=appointment_id
        )

        if not availability["available"]:
            raise AppointmentTimeConflictError(availability["message"])

        # Update appointment
        appointment.appointment_date = new_date
        appointment.appointment_time = new_time
        appointment.status = AppointmentStatus.RESCHEDULED.value
        appointment.reschedule_reason = reschedule_reason
        appointment.rescheduled_by = staff_member
        appointment.rescheduled_at = timezone.now()
        appointment.modified_by = staff_member
        appointment.save()

        return appointment

    @staticmethod
    def mark_as_completed(
        appointment_id: str,
        staff_member: Any,
        completion_notes: str | None = None
    ) -> Any:
        """Mark an appointment as completed."""
        PatientAppointment = apps.get_model("patients", "PatientAppointment")
        appointment = PatientAppointment.objects.get(id=appointment_id)

        if appointment.status == AppointmentStatus.CANCELED.value:
            raise ValidationError("Cannot complete canceled appointment")

        if appointment.status == AppointmentStatus.COMPLETED.value:
            raise ValidationError("Appointment is already completed")

        appointment.status = AppointmentStatus.COMPLETED.value
        appointment.completion_notes = completion_notes
        appointment.completed_by = staff_member
        appointment.completed_at = timezone.now()
        appointment.modified_by = staff_member
        appointment.save()

        return appointment

    @staticmethod
    def mark_as_no_show(
        appointment_id: str,
        staff_member: Any,
        no_show_notes: str | None = None
    ) -> Any:
        """Mark an appointment as no-show."""
        PatientAppointment = apps.get_model("patients", "PatientAppointment")
        appointment = PatientAppointment.objects.get(id=appointment_id)

        if appointment.status not in [AppointmentStatus.PENDING.value,
                                    AppointmentStatus.CONFIRMED.value]:
            raise ValidationError(f"Cannot mark {appointment.status} appointment as no-show")

        appointment.status = AppointmentStatus.NO_SHOW.value
        appointment.no_show_notes = no_show_notes
        appointment.no_show_marked_by = staff_member
        appointment.no_show_marked_at = timezone.now()
        appointment.modified_by = staff_member
        appointment.save()

        return appointment

    @staticmethod
    def get_appointment_history(
        patient_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
        status: list[str] | None = None
    ) -> list[Any]:
        """Get appointment history for a patient with filters."""
        PatientAppointment = apps.get_model("patients", "PatientAppointment")
        query = Q(patient_id=patient_id)

        if start_date:
            query &= Q(appointment_date__gte=start_date)
        if end_date:
            query &= Q(appointment_date__lte=end_date)
        if status:
            query &= Q(status__in=status)

        return PatientAppointment.objects.filter(query).order_by("-appointment_date",
                                                               "-appointment_time")

    @staticmethod
    def get_physician_schedule(
        physician_id: str,
        start_date: date,
        end_date: date,
        department_id: str | None = None
    ) -> dict[date, list[Any]]:
        """Get physician's schedule for a date range."""
        PatientAppointment = apps.get_model("patients", "PatientAppointment")
        appointments = PatientAppointment.objects.filter(
            physician_id=physician_id,
            appointment_date__range=[start_date, end_date],
            status__in=[
                AppointmentStatus.PENDING.value,
                AppointmentStatus.CONFIRMED.value,
                AppointmentStatus.RESCHEDULED.value
            ]
        ).order_by("appointment_date", "appointment_time")

        schedule = {}
        current_date = start_date
        while current_date <= end_date:
            day_schedule = SchedulePatternService.get_schedule_pattern(
                physician_id, department_id
            ).get(current_date.strftime("%A").lower())

            if day_schedule:
                schedule[current_date] = {
                    "working_hours": day_schedule,
                    "appointments": [
                        apt for apt in appointments
                        if apt.appointment_date == current_date
                    ]
                }
            current_date += timedelta(days=1)

        return schedule

    @staticmethod
    def get_department_schedule(
        department_id: str,
        target_date: date
    ) -> dict[str, list[Any]]:
        """Get schedule for all physicians in a department for a specific date."""
        schedule = {}
        physicians = DoctorProfile.objects.filter(
            departments__id=department_id,
            role__name="Doctor",
            is_active=True
        )

        for physician in physicians:
            day_schedule = SchedulePatternService.get_schedule_pattern(
                physician.id, department_id
            ).get(target_date.strftime("%A").lower())

            if day_schedule:
                PatientAppointment = apps.get_model("patients", "PatientAppointment")
                appointments = PatientAppointment.objects.filter(
                    physician_id=physician.id,
                    appointment_date=target_date,
                    status__in=[
                        AppointmentStatus.PENDING.value,
                        AppointmentStatus.CONFIRMED.value,
                        AppointmentStatus.RESCHEDULED.value
                    ]
                ).order_by("appointment_time")

                schedule[str(physician.id)] = {
                    "physician_name": f"{physician.first_name} {physician.last_name}",
                    "working_hours": day_schedule,
                    "appointments": appointments
                }

        return schedule
