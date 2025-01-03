from datetime import date

from django.db import transaction
from rest_framework import serializers

from apps.patients.permissions import PermissionCheckedSerializerMixin

from .models import Patient, PatientAddress, PatientDemographics


class PatientAddressSerializer(
    PermissionCheckedSerializerMixin, serializers.ModelSerializer
):
    """
    Serializer for patient addresses with validation.
    """

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
            "is_primary",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Check if user has change permission for demographics
        if not self.check_permission("add", "patientaddress"):
            # Make all fields read-only if no change permission
            for field_name in self.fields:
                self.fields[field_name].read_only = True

    def validate(self, data):
        # Ensure at least one address is marked as primary
        if data.get("is_primary", False):
            # If this address is being marked as primary, update other addresses
            patient = self.context.get("patient")
            if patient:
                PatientAddress.objects.filter(patient=patient).update(is_primary=False)
        return data


class PatientDemographicsSerializer(serializers.ModelSerializer):
    """
    Serializer for patient demographics with additional computed fields.
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
            "allergies",
            "gender",
            "race",
            "ethnicity",
            "preferred_language",
            "marital_status",
            "employment_status",
            "emergency_contact_name",
            "emergency_contact_phone",
            "chronic_conditions",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "bmi"]

    def get_bmi(self, obj):
        if obj.height_cm and obj.weight_kg:
            height_m = float(obj.height_cm) / 100
            bmi = float(obj.weight_kg) / (height_m * height_m)
            return round(bmi, 2)
        return None

    def validate_allergies(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Allergies must be a list")
        return value

    def validate_chronic_conditions(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Chronic conditions must be a list")
        return value


class PatientListCreateSerializer(
    PermissionCheckedSerializerMixin, serializers.ModelSerializer
):
    """
    Simplified serializer for list views with essential information.
    """

    demographics = PatientDemographicsSerializer(required=False)
    addresses = PatientAddressSerializer(many=True, required=False)
    full_name = serializers.SerializerMethodField()
    age = serializers.SerializerMethodField()
    primary_address = serializers.SerializerMethodField()

    class Meta:
        model = Patient
        fields = [
            "id",
            "first_name",
            "middle_name",
            "last_name",
            "full_name",
            "date_of_birth",
            "age",
            "gender",
            "email",
            "phone_primary",
            "phone_secondary",
            "preferred_language",
            "is_active",
            "demographics",
            "addresses",
            "primary_address",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "full_name", "age"]

    def validate(self, data):
        # Check create/update permissions based on whether instance exists
        is_update = self.instance is not None

        if is_update and not self.check_permission("view", "patient"):
            raise serializers.ValidationError(
                {"error": "You don't have permission to update patient information"}
            )
        if not is_update and not self.check_permission("add", "patient"):
            raise serializers.ValidationError(
                {"error": "You don't have permission to create patients"}
            )

        # Validate demographics permissions
        if "demographics" in data:
            if is_update and not self.check_permission("add", "patientdemographics"):
                raise serializers.ValidationError(
                    {"demographics": "You don't have permission to update demographics"}
                )
            if not is_update and not self.check_permission(
                "view", "patientdemographics"
            ):
                raise serializers.ValidationError(
                    {"demographics": "You don't have permission to add demographics"}
                )

        # Validate address permissions
        if "addresses" in data:
            if is_update and not self.check_permission("change", "patientaddress"):
                raise serializers.ValidationError(
                    {"addresses": "You don't have permission to update addresses"}
                )
            if not is_update and not self.check_permission("add", "patientaddress"):
                raise serializers.ValidationError(
                    {
                        "addresses": "You don't have permission to add addresses from validation"
                    }
                )

        return data

    def get_full_name(self, obj):
        if obj.middle_name:
            return f"{obj.first_name} {obj.middle_name} {obj.last_name}".strip()
        return f"{obj.first_name} {obj.last_name}".strip()

    def get_age(self, obj):
        today = date.today()  # noqa: DTZ011
        return (
            today.year
            - obj.date_of_birth.year
            - (
                (today.month, today.day)
                < (obj.date_of_birth.month, obj.date_of_birth.day)
            )
        )

    def get_primary_address(self, obj):
        primary_address = obj.addresses.filter(is_primary=True).first()
        if primary_address:
            return PatientAddressSerializer(primary_address).data
        return None

    def validate_email(self, value):
        instance = getattr(self, "instance", None)
        if instance and instance.email == value:
            return value

        if Patient.objects.filter(email=value).exists():
            raise serializers.ValidationError("This email is already in use.")
        return value

    @transaction.atomic
    def create(self, validated_data):
        demographics_data = validated_data.pop("demographics", None)
        addresses_data = validated_data.pop("addresses", None)

        # Create the patient
        patient = Patient.objects.create(**validated_data)

        # Handle demographics if provided and permitted
        if demographics_data and self.check_permission("add", "patientdemographics"):
            PatientDemographics.objects.create(patient=patient, **demographics_data)

        # Handle addresses if provided and permitted
        if addresses_data and self.check_permission("add", "patientaddress"):
            for address_data in addresses_data:
                PatientAddress.objects.create(patient=patient, **address_data)

        return patient

    @transaction.atomic
    def update(self, instance, validated_data):
        demographics_data = validated_data.pop("demographics", None)
        addresses_data = validated_data.pop("addresses", None)

        # Update patient fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update demographics if provided and permitted
        if demographics_data and self.check_permission("change", "patientdemographics"):
            demographics = instance.demographics
            for attr, value in demographics_data.items():
                setattr(demographics, attr, value)
            demographics.save()

        # Update addresses if provided and permitted
        if addresses_data is not None and self.check_permission(
            "change", "patientaddress"
        ):
            instance.addresses.all().delete()
            for address_data in addresses_data:
                PatientAddress.objects.create(patient=instance, **address_data)

        return instance

    def to_representation(self, instance):
        """
        Optimize query for list view by using select_related and prefetch_related.
        """
        representation = super().to_representation(instance)

        # If this is a list view (multiple instances), we've already prefetched the related data
        if not hasattr(instance, "_prefetched_objects_cache"):
            instance = (
                Patient.objects.select_related("demographics")
                .prefetch_related("addresses")
                .get(id=instance.id)
            )

        return representation
