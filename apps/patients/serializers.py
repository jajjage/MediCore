from django.db import transaction
from django.utils.timezone import now
from rest_framework import serializers

from .mixins.patients_mixins import (
    AppointmentValidator,
    OperationValidator,
    PatientCalculationMixin,
    PatientCreateMixin,
    PatientRelatedOperationsMixin,
    PatientUpdateMixin,
)
from .model_perm import check_model_permissions, prescription_preiod
from .models import (
    Patient,
    PatientAddress,
    PatientAllergies,
    PatientAppointment,
    PatientChronicConditions,
    PatientDemographics,
    PatientDiagnosis,
    PatientEmergencyContact,
    PatientMedicalReport,
    PatientOperation,
    PatientPrescription,
    PatientVisit,
)
from .permissions import PermissionCheckedSerializerMixin


class BasePatientSerializer(
    PermissionCheckedSerializerMixin, serializers.ModelSerializer
):
    """Base serializer with common patient-related functionality."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_permissions()

    def set_permissions(self):
        """Set field permissions based on user access."""
        model_name = self.Meta.model._meta.model_name
        if not self.check_permission("change", model_name):
            for field_name in self.fields:
                self.fields[field_name].read_only = True

    def validate_future_date(self, value, field_name):
        """Common validation for future dates."""  # noqa: D401
        if value and value > now().date():
            raise serializers.ValidationError(f"{field_name} cannot be in the future.")
        return value


class PatientAddressSerializer(BasePatientSerializer):
    """Serializer for patient addresses."""

    class Meta:
        model = PatientAddress
        fields = [
            "id",
            "address_type",
            "street_address1",
            "street_address2",
            "city",
            "state",
            "postal_code",
            "country",
        ]
        read_only_fields = ["id"]


class PatientDemographicsSerializer(BasePatientSerializer, PatientCalculationMixin):
    """Serializer for patient demographics."""

    bmi = serializers.SerializerMethodField()

    class Meta:
        model = PatientDemographics
        fields = [
            "id",
            "blood_type",
            "height_cm",
            "weight_kg",
            "bmi",
            "gender",
            "race",
            "ethnicity",
            "preferred_language",
            "marital_status",
            "employment_status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "bmi"]

    def get_bmi(self, obj):
        return self.calculate_bmi(obj.height_cm, obj.weight_kg)

    def validate(self, data):
        """Validate demographics data."""
        if self.instance:
            if not self.check_permission("change", "patientdemographics"):
                raise serializers.ValidationError(
                    {"error": "You don't have permission to update demographics"}
                )
        elif not self.check_permission("add", "patientdemographics"):
            raise serializers.ValidationError(
                {"error": "You don't have permission to add demographics"}
            )

        height_cm = data.get("height_cm")
        weight_kg = data.get("weight_kg")

        if height_cm is not None and height_cm <= 0:
            raise serializers.ValidationError(
                {"height_cm": "Height must be greater than 0"}
            )

        if weight_kg is not None and weight_kg <= 0:
            raise serializers.ValidationError(
                {"weight_kg": "Weight must be greater than 0"}
            )

        return data

    def to_representation(self, instance):
        """Control data visibility based on permissions."""
        if not self.check_permission("view", "patientdemographics"):
            return {}
        return super().to_representation(instance)


class PatientAllergySerializer(BasePatientSerializer):
    """Serializer for patient allergies."""

    class Meta:
        model = PatientAllergies
        fields = ["id", "name", "severity", "reaction"]
        read_only_fields = ["id"]

    def validate_severity(self, value):
        valid_severities = dict(PatientAllergies._meta.get_field("severity").choices)
        if value not in valid_severities:
            raise serializers.ValidationError(
                f"'{value}' is not a valid severity. Use one of {list(valid_severities.keys())}."
            )
        return value


class PatientChronicConditionSerializer(BasePatientSerializer):
    """Serializer for patient chronic conditions."""

    class Meta:
        model = PatientChronicConditions
        fields = ["id", "condition", "diagnosis_date", "notes"]
        read_only_fields = ["id"]

    def validate_diagnosis_date(self, value):
        return self.validate_future_date(value, "Diagnosis date")


class PatientEmergencyContactSerializer(BasePatientSerializer):
    """Serializer for patient emergency contacts."""

    class Meta:
        model = PatientEmergencyContact
        fields = ["id", "name", "phone", "relationship"]
        read_only_fields = ["id"]


class PatientMedicalReportSerializer(BasePatientSerializer):
    """Serializer for patient medical reports."""

    class Meta:
        model = PatientMedicalReport
        fields = ["id", "title", "description", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class PrescriptionSerializer(BasePatientSerializer, PatientCalculationMixin):
    physician_full_name = serializers.SerializerMethodField()
    class Meta:
        model = PatientPrescription
        fields = [
            "id",
            "appointment",
            "physician_full_name",
            "medicines",
            "instructions",
            "issued_date",
            "valid_until",
        ]
        read_only_fields = ["id", "issued_date", "issued_by", "appointment"]

    def validate(self, data):
        """
        Perform custom validation.
        """
        # Ensure valid_until date is not earlier than issued_date
        data = prescription_preiod(data)

        return data

    def validate_appointment(self, value):
        """
        Ensure the appointment has no existing prescription.
        """
        if value.prescription.exists():
            raise serializers.ValidationError(
                "A prescription already exists for this appointment."
            )
        return value

    def get_physician_full_name(self, obj):
        return self.physician_format_full_name(obj.issued_by.first_name, obj.issued_by.last_name)


class PatientVisitSerializer(BasePatientSerializer):
    """
    Serializer for patient visits with validation and history tracking.
    """

    class Meta:
        model = PatientVisit
        fields = [
            "id",
            "patient",
            "visit_date",
            "physician",
            "ward_or_clinic",
            "discharge_date",
            "discharge_notes",
            "referred_by",
        ]
        read_only_fields = ["id"]

    def validate(self, data):
        """
        Validate visit dates and permissions.
        """
        visit_date = data.get("visit_date")
        discharge_date = data.get("discharge_date")

        if visit_date and discharge_date and discharge_date < visit_date:
            raise serializers.ValidationError({
                "discharge_date": "Discharge date cannot be earlier than visit date."
            })

        # Ensure user has proper permissions
        if self.instance:
            if not self.check_permission("change", "patientvisit"):
                raise serializers.ValidationError(
                    {"error": "You don't have permission to update visits"}
                )
        elif not self.check_permission("add", "patientvisit"):
            raise serializers.ValidationError(
                {"error": "You don't have permission to add visits"}
            )

        return data

    def to_representation(self, instance):
        """
        Control data visibility based on permissions.
        """
        if not self.check_permission("view", "patientvisit"):
            return {}
        return super().to_representation(instance)

class PatientOperationSerializer(BasePatientSerializer, PatientCalculationMixin):
    """
    Serializer for patient operations with validation and history tracking.
    """

    surgeon_full_name = serializers.SerializerMethodField()
    patient_full_name = serializers.SerializerMethodField()
    class Meta:
        model = PatientOperation
        fields = [
            "id",
            "patient_full_name",
            "surgeon_full_name",
            "operation_date",
            "operation_time",
            "operation_name",
            "operation_code",
            "status",
            "notes",
        ]
        read_only_fields = ["id", "surgeon", "patient", "modified_by"]

    def validate_operation_date(self, value):
        """Validate operation date is not in the future."""
        return self.validate_date_not_future(value, "Operation date")

    def validate(self, data):
        """Validate operation data and permissions."""
        # Validate appointment datetime
        operation_date = data.get("operation_date",
                                 getattr(self.instance, "operation_date", None))
        operation_time = data.get("operation_time",
                                 getattr(self.instance, "operation_time", None))

        OperationValidator.validate_operation_datetime(
            operation_date,
            operation_time,
            self.instance
        )

        OperationValidator.validate_time_slot(
            operation_date,
            operation_time,
            self.context["request"].user,
            self.instance
        )
        if self.instance:
            if not self.check_permission("change", "patientoperation"):
                raise serializers.ValidationError(
                    {"error": "You don't have permission to update operations"}
                )
        elif not self.check_permission("add", "patientoperation"):
            raise serializers.ValidationError(
                {"error": "You don't have permission to add operations"}
            )

        return data

    def get_surgeon_full_name(self, obj):
        return self.physician_format_full_name(
            obj.surgeon.first_name,
            obj.surgeon.last_name
        )

    def get_patient_full_name(self, obj):
        return self.format_full_name(
            obj.patient.first_name,
            obj.patient.middle_name,
            obj.patient.last_name
        )
class PatientDiagnosisSerializer(BasePatientSerializer):
    """
    Serializer for patient diagnoses with validation and history tracking.
    """

    class Meta:
        model = PatientDiagnosis
        fields = [
            "id",
            "patient",
            "diagnosis_date",
            "diagnosis_name",
            "icd_code",
            "notes",
        ]
        read_only_fields = ["id"]

    def validate_diagnosis_date(self, value):
        """Validate diagnosis date is not in the future."""
        return self.validate_date_not_future(value, "Diagnosis date")

    def validate(self, data):
        """Validate diagnosis data and permissions."""
        if self.instance:
            if not self.check_permission("change", "patientdiagnosis"):
                raise serializers.ValidationError(
                    {"error": "You don't have permission to update diagnoses"}
                )
        elif not self.check_permission("add", "patientdiagnosis"):
            raise serializers.ValidationError(
                {"error": "You don't have permission to add diagnoses"}
            )

        return data

class PatientAppointmentSerializer(BasePatientSerializer, PatientCalculationMixin):
    physician_full_name = serializers.SerializerMethodField()
    patient_full_name = serializers.SerializerMethodField()
    current_prescription = serializers.SerializerMethodField()

    class Meta:
        model = PatientAppointment
        fields = [
            "id",
            "patient_full_name",
            "physician_full_name",
            "appointment_date",
            "appointment_time",
            "duration_minutes",
            "reason",
            "category",
            "status",
            "notes",
            "color_code",
            "is_recurring",
            "recurrence_pattern",
            "current_prescription",
        ]
        read_only_fields = [
            "id",
            "created_by",
            "modified_by",
            "last_modified",
            "patient",
            "physician",
        ]

    def validate(self, data):
        # Validate recurring appointment settings
        AppointmentValidator.validate_recurrence(
            data.get("is_recurring"),
            data.get("recurrence_pattern")
        )

        # Validate appointment datetime
        appointment_date = data.get("appointment_date",
                                 getattr(self.instance, "appointment_date", None))
        appointment_time = data.get("appointment_time",
                                 getattr(self.instance, "appointment_time", None))

        AppointmentValidator.validate_appointment_datetime(
            appointment_date,
            appointment_time,
            self.instance
        )

        # Validate time slot availability
        AppointmentValidator.validate_time_slot(
            appointment_date,
            appointment_time,
            self.context["request"].user,
            self.instance
        )

        return data

    def get_physician_full_name(self, obj):
        return self.physician_format_full_name(
            obj.physician.first_name,
            obj.physician.last_name
        )

    def get_patient_full_name(self, obj):
        return self.format_full_name(
            obj.patient.first_name,
            obj.patient.middle_name,
            obj.patient.last_name
        )

    def get_current_prescription(self, obj):
        prescription = getattr(obj, "prescription", None)
        if prescription:
            return {
                "id": prescription.id,
                "medicines": prescription.medicines,
                "instructions": prescription.instructions,
                "issued_date": prescription.issued_date,
                "valid_until": prescription.valid_until,
            }
        return None


class CompletePatientSerializer(
    BasePatientSerializer,
    PatientCalculationMixin,
    PatientCreateMixin,
    PatientUpdateMixin,
    PatientRelatedOperationsMixin,
):
    """Comprehensive serializer for detailed patient information."""

    allergies = PatientAllergySerializer(many=True, required=False)
    chronic_conditions = PatientChronicConditionSerializer(many=True, required=False)
    emergency_contact = PatientEmergencyContactSerializer(required=False)
    demographics = PatientDemographicsSerializer(required=False)
    addresses = PatientAddressSerializer(many=True, required=False)
    medical_reports = PatientMedicalReportSerializer(many=True, required=False)
    visits = PatientVisitSerializer(many=True, read_only=True)
    operations = PatientOperationSerializer(many=True, read_only=True)
    diagnoses = PatientDiagnosisSerializer(many=True, read_only=True)
    appointments = PatientAppointmentSerializer(many=True, read_only=True)
    full_name = serializers.SerializerMethodField()
    age = serializers.SerializerMethodField()
    pin = serializers.SerializerMethodField()
    nin_number = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Patient
        fields = [
            "id",
            "pin",
            "first_name",
            "middle_name",
            "last_name",
            "full_name",
            "date_of_birth",
            "age",
            "gender",
            "email",
            "phone_primary",
            "nin_number",
            "is_active",
            "created_at",
            "updated_at",
            "allergies",
            "chronic_conditions",
            "emergency_contact",
            "demographics",
            "addresses",
            "medical_reports",
            "visits",
            "operations",
            "diagnoses",
            "appointments"
        ]
        read_only_fields = ["id", "pin", "created_at", "updated_at"]

    def validate(self, data):
        # Check create/update permissions based on whether instance exists
        is_update = self.instance is not None

        data = check_model_permissions(self, data, is_update)

        return data

    def get_pin(self, obj):
        request = self.context.get("request")
        if not request:
            return None
        try:
            return obj.generate_pin(request)
        except ValueError as e:
            raise serializers.ValidationError from e

    def get_full_name(self, obj):
        return self.format_full_name(obj.first_name, obj.middle_name, obj.last_name)

    def get_age(self, obj):
        return self.calculate_age(obj.date_of_birth)

    def validate_email(self, value):
        instance = getattr(self, "instance", None)
        if instance and instance.email == value:
            return value

        if Patient.objects.filter(email=value).exists():
            raise serializers.ValidationError("This email is already in use.")
        return value

    @transaction.atomic
    def create(self, validated_data):
        if not self.check_permission("add", "patient"):
            raise serializers.ValidationError(
                {"error": "You don't have permission to create patients"}
            )

        allergies_data = validated_data.pop("allergies", [])
        chronic_conditions_data = validated_data.pop("chronic_conditions", [])
        emergency_contact_data = validated_data.pop("emergency_contact", None)
        addresses_data = validated_data.pop("addresses", [])
        nin_number = validated_data.pop("nin_number", None)
        demographics = validated_data.pop("demographics", {})

        patient = Patient.objects.create(**validated_data)

        if nin_number:
            patient.nin_number = nin_number
            patient.save()

        self._create_emergency_contact(patient, emergency_contact_data)
        self._create_allergies(patient, allergies_data)
        self._create_chronic_conditions(patient, chronic_conditions_data)
        self._create_addresses(patient, addresses_data)
        self._create_demogrphics(patient, demographics)

        return patient

    @transaction.atomic
    def update(self, instance, validated_data):
        if not self.check_permission("change", "patient"):
            raise serializers.ValidationError(
                {"error": "You don't have permission to update patients"}
            )

        allergies_data = validated_data.pop("allergies", None)
        chronic_conditions_data = validated_data.pop("chronic_conditions", None)
        emergency_contact_data = validated_data.pop("emergency_contact", None)
        addresses_data = validated_data.pop("addresses", None)
        nin_number = validated_data.pop("nin_number", None)

        # Update patient fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if nin_number is not None:
            instance.nin_number = nin_number

        instance.save()

        # Update related objects
        self._update_emergency_contact(instance, emergency_contact_data)
        self._update_allergies(instance, allergies_data)
        self._update_chronic_conditions(instance, chronic_conditions_data)
        self._update_addresses(instance, addresses_data)

        return instance

    def to_representation(self, instance):
        """Optimize query for detailed view."""
        if instance.id and not hasattr(instance, "_prefetched_objects_cache"):
            instance = (
                Patient.objects.select_related("demographics", "emergency_contact")
                .prefetch_related(
                    "allergies", "chronic_conditions", "addresses", "medical_reports"
                )
                .get(id=instance.id)
            )
        return super().to_representation(instance)


class PatientSearchSerializer(BasePatientSerializer, PatientCalculationMixin):
    """Lightweight serializer for patient search results."""

    full_name = serializers.SerializerMethodField()
    age = serializers.SerializerMethodField()

    class Meta:
        model = Patient
        fields = [
            "id",
            "pin",
            "first_name",
            "middle_name",
            "last_name",
            "full_name",
            "date_of_birth",
            "age",
            "gender",
            "email",
            "phone_primary",
            "is_active",
        ]

    def get_full_name(self, obj):
        return self.format_full_name(obj.first_name, obj.middle_name, obj.last_name)

    def get_age(self, obj):
        return self.calculate_age(obj.date_of_birth)

    def to_representation(self, instance):
        """Optimize query for search results."""
        if instance.id and not hasattr(instance, "_prefetched_objects_cache"):
            instance = Patient.objects.select_related("demographics").get(
                id=instance.id
            )
        return super().to_representation(instance)
