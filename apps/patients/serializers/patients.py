from django.contrib.auth import get_user_model
from django.db import transaction

# tenant_app/serializers.py (tenant schema)
from django_tenants.utils import schema_context
from rest_framework import serializers

from apps.patients.mixins.patients_mixins import (
    CalculationMixin,
    PatientCreateMixin,
    PatientRelatedOperationsMixin,
    PatientUpdateMixin,
)
from apps.patients.model_perm import check_model_permissions
from apps.patients.models import (
    Patient,
    PatientDemographics,
    PatientEmergencyContact,
)
from hospital.models import HospitalMembership

from .appointment_serializer import PatientAppointmentSerializer
from .base_serializer import BasePatientSerializer
from .diagnosis_serializer import PatientDiagnosisSerializer
from .medical_serializer import (
    PatientAllergySerializer,
    PatientChronicConditionSerializer,
)
from .operation_serializer import PatientOperationSerializer
from .report_serializer import PatientMedicalReportSerializer
from .visit_serializer import PatientVisitSerializer

User = get_user_model()
class UserSerializer(serializers.ModelSerializer):
    role = serializers.CharField(
        write_only=True,
        required=True,
        help_text="Role of the user in the hospital (e.g., 'doctor', 'admin')."
    )
    user_role = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "middle_name", "password", "role", "user_role"]
        read_only_fields = ["id", "user_role"]
        extra_kwargs = {"password": {"write_only": True}}

    def get_user_role(self, obj):
        # Fetch role from HospitalMembership in the public schema
        with schema_context("public"):
            membership = HospitalMembership.objects.get(user=obj, hospital_profile=self.context["hospital"])
            return str(membership.role.name)

    def create(self, validated_data):
        # Get the hospital from the context (set in the view)
        hospital = self.context["hospital"]
        tenant = self.context["tenant"]
        role = self.context["role"]
        is_tenant_admin = validated_data["role"] == "Tenant Admin"

        # Switch to public schema to create User and HospitalMembership
        with transaction.atomic(), schema_context("public"):
            # Create user with hashed password
            user = User.objects.create_user(
                email=validated_data["email"],
                first_name=validated_data["first_name"],
                last_name=validated_data["last_name"],
                middle_name=validated_data["middle_name"],
                password=validated_data["password"]
            )
            # Link user to the hospital
            HospitalMembership.objects.create(
                user=user,
                tenant=tenant,
                hospital_profile=hospital,
                role=role,
                is_tenant_admin=is_tenant_admin)

        return user
class PatientDemographicsSerializer(BasePatientSerializer, CalculationMixin):
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

class PatientEmergencyContactSerializer(BasePatientSerializer):
    """Serializer for patient emergency contacts."""

    class Meta:
        model = PatientEmergencyContact
        fields = "__all__"
        read_only_fields = ["id"]


class CompletePatientSerializer(
    BasePatientSerializer,
    CalculationMixin,
    PatientCreateMixin,
    PatientUpdateMixin,
    PatientRelatedOperationsMixin,
):
    """Comprehensive serializer for detailed patient information."""

    allergies = PatientAllergySerializer(many=True, required=False)
    chronic_conditions = PatientChronicConditionSerializer(many=True, required=False)
    emergency_contact = PatientEmergencyContactSerializer(required=False)
    demographics = PatientDemographicsSerializer(required=False)
    medical_reports = PatientMedicalReportSerializer(many=True, required=False)
    visits = PatientVisitSerializer(many=True, read_only=True)
    operations = PatientOperationSerializer(many=True, read_only=True)
    diagnoses = PatientDiagnosisSerializer(many=True, read_only=True)
    appointments = PatientAppointmentSerializer(many=True, read_only=True)
    full_name = serializers.SerializerMethodField()
    pin = serializers.CharField(read_only=True)
    nin_number = serializers.CharField(write_only=True, required=False)
    documentation_urls = serializers.SerializerMethodField()  # New field

    class Meta:
        model = Patient
        fields = [
            "id",
            "pin",
            "full_name",
            "date_of_birth",
            "nin_number",
            "is_active",
            "created_at",
            "updated_at",
            "allergies",
            "chronic_conditions",
            "emergency_contact",
            "demographics",
            "medical_reports",
            "visits",
            "operations",
            "diagnoses",
            "appointments",
            "documentation_urls"  # Added to fields
        ]
        read_only_fields = ["id", "pin", "created_at", "updated_at", "documentation_urls"]

    def validate(self, data):
        # Check create/update permissions based on whether instance exists
        is_update = self.instance is not None

        data = check_model_permissions(self, data, is_update)

        return data

    def get_documentation_urls(self, obj):
        """Generate endpoint URLs for frontend navigation."""
        request = self.context.get("request")
        base_path = f"/api/v1/patients/{obj.id}/"
        return {
            "emergency_contacts": request.build_absolute_uri(f"{base_path}emergency-contact") if request else base_path + "emergencycontact/",
            "chronic_conditions": request.build_absolute_uri(f"{base_path}chronic-condition") if request else base_path + "chroniccondition/",
            "demographics": request.build_absolute_uri(f"{base_path}demographics") if request else base_path + "demographics/",
            "medical_history": request.build_absolute_uri(f"{base_path}medicalhistory") if request else base_path + "medicalhistory/"
        }

    def get_full_name(self, obj):
        return self.format_full_name(obj.user.first_name, obj.user.middle_name, obj.user.last_name)

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
        nin_number = validated_data.pop("nin_number", None)
        demographics = validated_data.pop("demographics", {})

        patient = Patient.objects.create( **validated_data)

        if nin_number:
            patient.nin_number = nin_number
            patient.save()

        self._create_emergency_contact(patient, emergency_contact_data)
        self._create_allergies(patient, allergies_data)
        self._create_chronic_conditions(patient, chronic_conditions_data)
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

        return instance


    def to_representation(self, instance):
        """Ensure consistent empty state representation and optimize queries."""
        # Optimize database queries
        if instance.id and not hasattr(instance, "_prefetched_objects_cache"):
            instance = Patient.objects.select_related(
                "user",
                "emergency_contact",
                "demographics"
            ).prefetch_related(
                "allergies",
                "chronic_conditions",
                "medical_reports",
                "visits",
                "operations",
                "diagnoses",
                "appointments"
            ).get(id=instance.id)

        representation = super().to_representation(instance)

        # Ensure empty arrays for list-type relationships
        list_fields = [
            "allergies", "chronic_conditions", "medical_reports",
            "visits", "operations", "diagnoses", "appointments"
        ]
        for field in list_fields:
            if not representation.get(field):
                representation[field] = []

        # Set null for uninitialized single-object relationships
        single_object_fields = ["emergency_contact", "demographics"]
        for field in single_object_fields:
            if not representation.get(field):
                representation[field] = None

        return representation

class PatientSearchSerializer(BasePatientSerializer, CalculationMixin):
    """Lightweight serializer for patient search results."""

    full_name = serializers.SerializerMethodField()
    age = serializers.SerializerMethodField()
    first_name = serializers.CharField(source="user.first_name")
    middle_name = serializers.CharField(source="user.middle_name")
    last_name = serializers.CharField(source="user.last_name")

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
        return self.format_full_name(obj.user.first_name, obj.user.middle_name, obj.user.last_name)

    def get_age(self, obj):
        return self.calculate_age(obj.date_of_birth)

    def to_representation(self, instance):
        """Optimize query for search results."""
        if instance.id and not hasattr(instance, "_prefetched_objects_cache"):
            instance = Patient.objects.select_related("demographics").get(
                id=instance.id
            )
        return super().to_representation(instance)
