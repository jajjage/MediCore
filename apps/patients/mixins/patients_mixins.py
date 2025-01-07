from django.utils.timezone import now

from apps.patients.models import (
    PatientAddress,
    PatientAllergy,
    PatientChronicCondition,
    PatientDemographics,
    PatientEmergencyContact,
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
        today = now().date()
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
            "allergies": PatientAllergy,
            "chronic_conditions": PatientChronicCondition,
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
        if self.check_permission("add", "patientallergy"):
            for allergy_data in allergies_data:
                PatientAllergy.objects.create(patient=patient, **allergy_data)

    def _create_chronic_conditions(self, patient, chronic_conditions_data):
        if self.check_permission("add", "patientchroniccondition"):
            for condition_data in chronic_conditions_data:
                PatientChronicCondition.objects.create(
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
                PatientAllergy.objects.create(patient=instance, **allergy_data)

    def _update_chronic_conditions(self, instance, chronic_conditions_data):
        if chronic_conditions_data is not None and self.check_permission(
            "change", "patientchroniccondition"
        ):
            instance.chronic_conditions.all().delete()
            for condition_data in chronic_conditions_data:
                PatientChronicCondition.objects.create(
                    patient=instance, **condition_data
                )

    def _update_addresses(self, instance, addresses_data):
        if addresses_data is not None and self.check_permission(
            "change", "patientaddress"
        ):
            instance.addresses.all().delete()
            for address_data in addresses_data:
                PatientAddress.objects.create(patient=instance, **address_data)
