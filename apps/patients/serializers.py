from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from apps.patients.model_perm import check_model_permissions
from apps.patients.permissions import PermissionCheckedSerializerMixin

from .models import (
    Patient,
    PatientAddress,
    PatientAllergy,
    PatientChronicCondition,
    PatientDemographics,
    PatientEmergencyContact,
    PatientMedicalReport,
)


class PatientAddressSerializer(
    PermissionCheckedSerializerMixin, serializers.ModelSerializer
):
    """Serializer for patient addresses with permissions."""

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


class PatientDemographicsSerializer(
    PermissionCheckedSerializerMixin, serializers.ModelSerializer
):
    """
    Serializer for patient demographics with validation and permissions.
    """

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Make all fields read-only if user doesn't have change permission
        if not self.check_permission("change", "patientdemographics"):
            for field_name in self.fields:
                self.fields[field_name].read_only = True

    def get_bmi(self, obj):
        """Calculate BMI if height and weight are available."""
        if obj.height_cm and obj.weight_kg:
            height_m = float(obj.height_cm) / 100
            bmi = float(obj.weight_kg) / (height_m * height_m)
            return round(bmi, 2)
        return None

    def validate(self, data):
        """Validate demographics data."""
        # Check permissions
        if self.instance:
            if not self.check_permission("change", "patientdemographics"):
                raise serializers.ValidationError(
                    {"error": "You don't have permission to update demographics"}
                )
        elif not self.check_permission("add", "patientdemographics"):
            raise serializers.ValidationError(
                {"error": "You don't have permission to add demographics"}
            )

        # Validate height and weight if provided
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


class PatientAllergySerializer(
    PermissionCheckedSerializerMixin, serializers.ModelSerializer
):
    """
    Serializer for patient allergies with validation and permissions.
    """

    class Meta:
        model = PatientAllergy
        fields = ["id", "name", "severity", "reaction"]
        read_only_fields = ["id"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not self.check_permission("add", "patientallergy"):
            for field_name in self.fields:
                self.fields[field_name].read_only = True

    def validate_severity(self, value):
        valid_severities = dict(PatientAllergy._meta.get_field("severity").choices)
        if value not in valid_severities:
            raise serializers.ValidationError(
                f"'{value}' is not a valid severity. Use one of {list(valid_severities.keys())}."
            )
        return value


class PatientChronicConditionSerializer(
    PermissionCheckedSerializerMixin, serializers.ModelSerializer
):
    """
    Serializer for patient chronic conditions with permissions.
    """

    class Meta:
        model = PatientChronicCondition
        fields = ["id", "condition", "diagnosis_date", "notes"]
        read_only_fields = ["id"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not self.check_permission("add", "patientchroniccondition"):
            for field_name in self.fields:
                self.fields[field_name].read_only = True

    def validate_diagnosis_date(self, value):
        if value and value > timezone.now().date():
            raise serializers.ValidationError("Diagnosis date cannot be in the future.")
        return value
        return value


class PatientEmergencyContactSerializer(
    PermissionCheckedSerializerMixin, serializers.ModelSerializer
):
    """
    Serializer for patient emergency contacts with permissions.
    """

    class Meta:
        model = PatientEmergencyContact
        fields = ["id", "name", "phone", "relationship"]
        read_only_fields = ["id"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not self.check_permission("add", "patientemergencycontact"):
            for field_name in self.fields:
                self.fields[field_name].read_only = True


class PatientMedicalReportSerializer(
    PermissionCheckedSerializerMixin, serializers.ModelSerializer
):
    class Meta:
        model = PatientMedicalReport
        fields = ["id", "title", "description", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Debug print
        print("Serializer context:", self.context)

        # Make sure we're using the correct model name
        model_name = "patientmedicalreport"
        if not self.check_permission("add", model_name):
            print(f"No permission for add_{model_name}")
            for field_name in self.fields:
                self.fields[field_name].read_only = True


class CompletePatientSerializer(
    PermissionCheckedSerializerMixin, serializers.ModelSerializer
):
    """
    Comprehensive serializer for detailed patient information including all related data.

    Includes permission checks for all operations.
    """

    allergies = PatientAllergySerializer(many=True, required=False)
    chronic_conditions = PatientChronicConditionSerializer(many=True, required=False)
    emergency_contact = PatientEmergencyContactSerializer(required=False)
    demographics = PatientDemographicsSerializer(required=False)
    addresses = PatientAddressSerializer(many=True, required=False)
    medical_reports = PatientMedicalReportSerializer(many=True, required=False)
    full_name = serializers.SerializerMethodField()
    age = serializers.SerializerMethodField()
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
        ]
        read_only_fields = ["id", "pin", "created_at", "updated_at"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not self.check_permission("view", "patient"):
            for field_name in self.fields:
                self.fields[field_name].read_only = True

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
            # Handle the error appropriately
            raise serializers.ValidationError from e

    def get_demographics(self, obj):
        if not self.check_permission("view", "patientdemographics"):
            return None

        if hasattr(obj, "demographics"):
            return {
                "blood_type": obj.demographics.blood_type,
                "height_cm": obj.demographics.height_cm,
                "weight_kg": obj.demographics.weight_kg,
                "bmi": self.calculate_bmi(obj.demographics),
                "gender": obj.demographics.gender,
                "race": obj.demographics.race,
                "ethnicity": obj.demographics.ethnicity,
                "preferred_language": obj.demographics.preferred_language,
                "marital_status": obj.demographics.marital_status,
                "employment_status": obj.demographics.employment_status,
            }
        return None

    def calculate_bmi(self, demographics):
        if demographics.height_cm and demographics.weight_kg:
            height_m = float(demographics.height_cm) / 100
            bmi = float(demographics.weight_kg) / (height_m * height_m)
            return round(bmi, 2)
        return None

    def get_full_name(self, obj):
        if obj.middle_name:
            return f"{obj.first_name} {obj.middle_name} {obj.last_name}".strip()
        return f"{obj.first_name} {obj.last_name}".strip()

    def get_age(self, obj):
        today = timezone.now().date()
        return (
            today.year
            - obj.date_of_birth.year
            - (
                (today.month, today.day)
                < (obj.date_of_birth.month, obj.date_of_birth.day)
            )
        )

    def validate_email(self, value):
        instance = getattr(self, "instance", None)
        if instance and instance.email == value:
            return value

        if Patient.objects.filter(email=value).exists():
            raise serializers.ValidationError("This email is already in use.")
        return value

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
        """
        Optimize query for detailed view by using select_related and prefetch_related.
        """
        if instance.id and not hasattr(instance, "_prefetched_objects_cache"):
            instance = (
                Patient.objects.select_related("demographics", "emergency_contact")
                .prefetch_related(
                    "allergies", "chronic_conditions", "addresses", "medical_reports"
                )
                .get(id=instance.id)
            )
        return super().to_representation(instance)
