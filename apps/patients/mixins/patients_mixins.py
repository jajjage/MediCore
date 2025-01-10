from datetime import datetime

from django.utils import timezone
from rest_framework import serializers

from apps.patients.models import (
    PatientAddress,
    PatientAllergies,
    PatientAppointment,
    PatientChronicConditions,
    PatientDemographics,
    PatientEmergencyContact,
    PatientOperation,
)


class PatientCalculationMixin:
    """Mixin for common patient calculations."""

    def calculate_bmi(self, height_cm, weight_kg):
        """Calculate BMI from height and weight."""
        if height_cm and weight_kg:
            height_m = float(height_cm) / 100
            return round(float(weight_kg) / (height_m * height_m), 2)
        return None

    def calculate_age(self, date_of_birth):
        """Calculate age from date of birth."""
        today = timezone.now().date()
        return (
            today.year
            - date_of_birth.year
            - ((today.month, today.day) < (date_of_birth.month, date_of_birth.day))
        )

    def format_full_name(self, first_name, middle_name, last_name):
        """Generate full name with optional middle name."""
        if middle_name:
            return f"{first_name} {middle_name} {last_name}".strip()
        return f"{first_name} {last_name}".strip()

    def physician_format_full_name(self, first_name, last_name):
        """Generate full name with optional middle name."""
        return f"{first_name} {last_name}".strip()



class PatientRelatedOperationsMixin:
    """Mixin for handling related model operations."""

    def _handle_related_object(
        self, instance, data, model_class, permission_type, operation="create"
    ):
        """Handle a single related object."""
        if data and self.check_permission(
            permission_type, model_class._meta.model_name
        ):
            if operation == "update":
                model_class.objects.filter(patient=instance).delete()
            return model_class.objects.create(patient=instance, **data)
        return None

    def _handle_related_objects_list(
        self, instance, data_list, model_class, permission_type, operation="create"
    ):
        """Handle a lists related objects."""
        if data_list and self.check_permission(
            permission_type, model_class._meta.model_name
        ):
            if operation == "update":
                model_class.objects.filter(patient=instance).delete()
            return [
                model_class.objects.create(patient=instance, **data)
                for data in data_list
            ]
        return []

    def handle_related_objects(self, instance, validated_data, operation_type="create"):
        """Handle all related objects creation/updates."""
        # Handle emergency contact
        emergency_contact_data = validated_data.pop("emergency_contact", None)
        self._handle_related_object(
            instance,
            emergency_contact_data,
            PatientEmergencyContact,
            "add" if operation_type == "create" else "change",
            operation_type,
        )

        # Handle lists of related objects
        related_lists = {
            "allergies": PatientAllergies,
            "chronic_conditions": PatientChronicConditions,
            "addresses": PatientAddress,
        }

        for field, model in related_lists.items():
            data_list = validated_data.pop(field, [])
            self._handle_related_objects_list(
                instance,
                data_list,
                model,
                "add" if operation_type == "create" else "change",
                operation_type,
            )

        # Handle demographics
        demographics_data = validated_data.pop("demographics", None)
        if demographics_data:
            self._handle_related_object(
                instance,
                demographics_data,
                PatientDemographics,
                "add" if operation_type == "create" else "change",
                operation_type,
            )


class PatientCreateMixin:
    """Mixin for handling patient register."""

    def _create_emergency_contact(self, patient, emergency_contact_data):
        if emergency_contact_data and self.check_permission(
            "add", "patientemergencycontact"
        ):
            PatientEmergencyContact.objects.create(
                patient=patient, **emergency_contact_data
            )

    def _create_allergies(self, patient, allergies_data):
        if self.check_permission("add", "patientallergies"):
            for allergy_data in allergies_data:
                PatientAllergies.objects.create(patient=patient, **allergy_data)

    def _create_chronic_conditions(self, patient, chronic_conditions_data):
        if self.check_permission("add", "patientchronicconditions"):
            for condition_data in chronic_conditions_data:
                PatientChronicConditions.objects.create(
                    patient=patient, **condition_data
                )

    def _create_addresses(self, patient, addresses_data):
        if self.check_permission("add", "patientaddress"):
            for address_data in addresses_data:
                PatientAddress.objects.create(patient=patient, **address_data)

    def _create_demogrphics(self, patient, demographics):
        if self.check_permission("add", "patientdemographics"):
            for demographics_data in demographics:
                PatientDemographics.objects.create(patient=patient, **demographics_data)


class PatientUpdateMixin:
    """Mixin for updating the patient data."""

    def _update_emergency_contact(self, instance, emergency_contact_data):
        if emergency_contact_data is not None and self.check_permission(
            "change", "patientemergencycontact"
        ):
            PatientEmergencyContact.objects.update_or_create(
                patient=instance, defaults=emergency_contact_data
            )

    def _update_allergies(self, instance, allergies_data):
        if allergies_data is not None and self.check_permission(
            "change", "patientallergy"
        ):
            instance.allergies.all().delete()
            for allergy_data in allergies_data:
                PatientAllergies.objects.create(patient=instance, **allergy_data)

    def _update_chronic_conditions(self, instance, chronic_conditions_data):
        if chronic_conditions_data is not None and self.check_permission(
            "change", "patientchroniccondition"
        ):
            instance.chronic_conditions.all().delete()
            for condition_data in chronic_conditions_data:
                PatientChronicConditions.objects.create(
                    patient=instance, **condition_data
                )

    def _update_addresses(self, instance, addresses_data):
        if addresses_data is not None and self.check_permission(
            "change", "patientaddress"
        ):
            instance.addresses.all().delete()
            for address_data in addresses_data:
                PatientAddress.objects.create(patient=instance, **address_data)


class AppointmentValidator:
    @staticmethod
    def validate_appointment_datetime(appointment_date, appointment_time, instance=None):  # noqa: ARG004
        """
        Validate appointment date and time with proper timezone handling.
        """
        if appointment_date and appointment_time:
            # Combine date and time
            appointment_datetime = datetime.combine(appointment_date, appointment_time)

            # Make the appointment datetime timezone-aware using the current timezone
            appointment_datetime = timezone.make_aware(appointment_datetime)

            # Get current time (already timezone-aware)
            current_datetime = timezone.now()

            if appointment_datetime < current_datetime:
                raise serializers.ValidationError(
                    "Appointment cannot be scheduled in the past"
                )

    @staticmethod
    def validate_time_slot(appointment_date, appointment_time, physician, instance=None):
        """
        Check for appointment time slot conflicts.
        """
        conflicts = PatientAppointment.objects.filter(
            physician=physician,
            appointment_date=appointment_date,
            appointment_time=appointment_time
        )

        if physician.role.name != "Doctor":
            raise serializers.ValidationError("Selected staff member is not a doctor.")

        if instance:
            conflicts = conflicts.exclude(pk=instance.pk)

        if conflicts.exists():
            raise serializers.ValidationError(
                "This time slot is already booked"
            )

    @staticmethod
    def validate_recurrence(is_recurring, recurrence_pattern):
        """
        Validate recurring appointment data.
        """
        if is_recurring and not recurrence_pattern:
            raise serializers.ValidationError(
                "Recurrence pattern is required for recurring appointments"
            )

class OperationValidator:
    @staticmethod
    def validate_operation_datetime(operation_date, operation_time, instance=None):  # noqa: ARG004
        """
        Validate appointment date and time with proper timezone handling.
        """
        if operation_date and operation_time:
            # Combine date and time
            operation_datetime = datetime.combine(operation_date, operation_time)

            # Make the appointment datetime timezone-aware using the current timezone
            operation_datetime = timezone.make_aware(operation_datetime)

            # Get current time (already timezone-aware)
            current_datetime = timezone.now()

            if operation_datetime <= current_datetime:
                raise serializers.ValidationError(
                    "Operation cannot be scheduled in the past"
                )

    @staticmethod
    def validate_time_slot(operation_date, operation_time, surgeon, instance=None):
        """
        Check for operation time slot conflicts.
        """
        conflicts = PatientOperation.objects.filter(
            surgeon=surgeon,
            operation_date=operation_date,
            operation_time=operation_time
        )

        if instance:
            conflicts = conflicts.exclude(pk=instance.pk)

        if conflicts.exists():
            raise serializers.ValidationError(
                "This time slot is already booked"
            )
