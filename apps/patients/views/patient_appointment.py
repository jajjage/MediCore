from datetime import datetime

from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.patients.models import (
    PatientAppointment,
)
from apps.patients.serializers import (
    AppointmentStatusUpdateSerializer,
    AvailabilityCheckSerializer,
    PatientAppointmentCreateSerializer,
    PatientAppointmentSerializer,
    RecurringAppointmentSerializer,
    TimeSlotSerializer,
)
from apps.scheduling.services.schedule_service import (
    AppointmentService,
    AppointmentTimeConflictError,
    AppointmentTimeService,
    RecurringAppointmentService,
    SchedulePatternService,
)
from apps.staff.models.departments import Department
from base_view import BaseViewSet

User = get_user_model()
class PatientAppointmentViewSet(BaseViewSet):
    """
    ViewSet for managing patient appointments with comprehensive service integration.
    """

    def get_queryset(self):
        return  PatientAppointment.objects.filter(
           patient_id=self.kwargs.get("patient__pk")
            ).select_related(
                "physician",
                "department",
                "patient",
                "created_by",
                "modified_by"
            )

    def get_serializer_class(self):
        serializer_map = {
            "create": PatientAppointmentCreateSerializer,
            "update": PatientAppointmentCreateSerializer,
            "partial_update": PatientAppointmentCreateSerializer,
            "create_recurring": RecurringAppointmentSerializer,
            "check_availability": AvailabilityCheckSerializer,
            "update_status": AppointmentStatusUpdateSerializer,
            "list": PatientAppointmentSerializer,
            "retrieve": PatientAppointmentSerializer
        }
        return serializer_map.get(self.action, PatientAppointmentSerializer)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        physician_id=serializer.validated_data["physician"]
        department_id=serializer.validated_data["department"]
        week_start=serializer.validated_data["appointment_date"]

        try:
            try:
                schedule = SchedulePatternService.get_schedule_pattern(
                    physician_id=physician_id,
                    department_id=department_id,
                    week_start=week_start
                )
                print(schedule)
                AppointmentTimeService.is_within_schedule(schedule, serializer.validated_data["start_time"])
            except AppointmentTimeConflictError as e:
                return self.error_response(
                    message=f" {e.message} Time outside physician's working hours",
                    code=400,
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            try:
                department = Department.objects.get(
                    id=department_id,
                )
                physician = User.objects.get(
                    id=physician_id,
                    hospital_memberships_user__role__name="Doctor"
                )
            except (Department.DoesNotExist, User.DoesNotExist):
                raise ValidationError(
                    f"Department with ID {department_id} does not exist in this hospital"
                )

            appointment = AppointmentService.create_appointment(
                serializer,
                department,
                physician,
                self.request.user,
                self.kwargs.get("patient__pk"),
            )
            return self.success_response(
                data=PatientAppointmentSerializer(appointment).data,
                message="Appointment created successfully"
            )
        except ValidationError as e:
            return self.error_response(message=e.detail, code=400)

    @action(detail=False, methods=["post"])
    def create_recurring(self, request, patient__pk=None):
        serializer = RecurringAppointmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            appointments = RecurringAppointmentService.create_recurring_appointments(
                serializer=serializer,
                staff_member=self.request.user,
                patient_id=patient__pk
            )
            return self.success_response(
                data=PatientAppointmentSerializer(appointments, many=True).data,
                message="Recurring appointments created successfully"
            )
        except ValidationError as e:
            return self.validation_error(e.detail)

    @action(detail=False, methods=["post"])
    def check_availability(self, request, patient__pk=None):
        serializer = AvailabilityCheckSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = AppointmentService.get_physician_schedule(
            physician_id=serializer.validated_data["physician_id"],
            start_datetime=serializer.validated_data["start_datetime"],
            end_datetime=serializer.validated_data["end_datetime"],
            department_id=serializer.validated_data.get("department_id")
        )
        return self.success_response(data=result)

    @action(detail=False, methods=["get"])
    def available_slots(self, request, patient__pk=None):
        try:
            physician_id = request.query_params.get("physician_id")
            date_str = request.query_params.get("date")
            department_id = request.query_params.get("department_id")
            slot_duration = int(request.query_params.get("slot_duration", 30))

            if not physician_id or not date_str:
                return self.validation_error({
                    "physician_id": "Required field",
                    "date": "Required field"
                })

            date = datetime.strptime(date_str, "%Y-%m-%d%z").date()
            slots = AppointmentTimeService.get_available_slots(
                physician_id=physician_id,
                date=date,
                department_id=department_id,
                slot_duration=slot_duration
            )
            return self.success_response(
                data=TimeSlotSerializer(slots, many=True).data
            )
        except ValueError:
            return self.validation_error({"date": "Invalid date format"})

    @action(detail=True, methods=["patch", "get"])
    def reschedule(self, request, patient__pk=None, pk=None):
        try:
            appointment = self.get_object()
            appointment_id = appointment.id
            if request.method == "GET":
                serializer = self.get_serializer(appointment)
                return Response(serializer.data)
            if str(appointment.patient.pk) != str(patient__pk):
                return self.error_response(
                    message="Appointment does not belong to specified patient"
                )

            serializer = self.get_serializer(
                appointment,
                data=request.data,
                partial=True
            )
            if serializer.is_valid(raise_exception=True):
                try:
                    updated_appointment = AppointmentService.update_appointment(
                        appointment_id,
                        serializer,
                        self.request.user
                    )

                    return self.success_response(
                        data=PatientAppointmentSerializer(updated_appointment).data,
                        message="Appointment rescheduled successfully"
                    )
                except AppointmentTimeConflictError as e:
                    return self.error_response(
                        message=e.message,
                        status_code=status.HTTP_400_BAD_REQUEST
                    )
        except ObjectDoesNotExist:
            return self.not_found(resource_type="Appointment")
        except ValidationError as e:
            return self.error_response(message=e.detail, status_code=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post", "get"])
    def cancel(self, request, patient__pk=None, pk=None):
        try:
            appointment = self.get_object()
            if request.method == "GET":
                serializer = self.get_serializer(appointment)
                return Response(serializer.data)
            if appointment.status in ["completed", "cancelled", "rejected"]:
                return self.error_response(
                    message=f"Cannot cancel appointment with status: {appointment.status}"
                )

            with transaction.atomic():
                cancellation_reason = request.data.get("cancellation_reason", "")
                AppointmentService.cancel_appointment(
                    appointment.id,
                    self.request.user,
                    cancellation_reason
                )
                return self.success_response(
                    message="Appointment cancelled successfully"
                )
        except ObjectDoesNotExist:
            return self.not_found(resource_type="Appointment")

    @action(detail=True, methods=["patch", "get"])
    def update_status(self, request, patient__pk=None, pk=None):
        try:
            appointment = self.get_object()
            serializer = AppointmentStatusUpdateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            updated_appointment = AppointmentService.update_appointment_status(
                appointment,
                serializer.validated_data["status"],
                self.request.user,
                serializer.validated_data.get("notes")
            )
            return self.success_response(
                data=PatientAppointmentSerializer(updated_appointment).data,
                message=f"Appointment status updated to {updated_appointment.status}"
            )
        except ObjectDoesNotExist:
            return self.not_found(resource_type="Appointment")
        except ValidationError as e:
            return self.error_response(message=e.detail)
