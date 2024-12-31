from rest_framework import serializers
from .models import Patient, PatientDemographics, PatientAddress

class PatientAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientAddress
        fields = [
            'id', 'address_type', 'street_address1', 'street_address2',
            'city', 'state', 'postal_code', 'country', 'is_primary',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class PatientDemographicsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientDemographics
        fields = [
            'id', 'blood_type', 'height_cm', 'weight_kg',
            'allergies', 'chronic_conditions', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class PatientSerializer(serializers.ModelSerializer):
    demographics = PatientDemographicsSerializer(required=False)
    addresses = PatientAddressSerializer(many=True, required=False)

    class Meta:
        model = Patient
        fields = [
            'id', 'first_name', 'middle_name', 'last_name',
            'date_of_birth', 'gender', 'nin', 'email',
            'phone_primary', 'phone_secondary', 'preferred_language',
            'is_active', 'created_at', 'updated_at',
            'demographics', 'addresses'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'nin_encrypted']

    def create(self, validated_data):
        demographics_data = validated_data.pop('demographics', None)
        addresses_data = validated_data.pop('addresses', [])
        
        # Create the patient instance
        patient = Patient.objects.create(**validated_data)
        
        # Create demographics if provided
        if demographics_data:
            PatientDemographics.objects.create(patient=patient, **demographics_data)
        
        # Create addresses if provided
        for address_data in addresses_data:
            PatientAddress.objects.create(patient=patient, **address_data)
        
        return patient

    def update(self, instance, validated_data):
        demographics_data = validated_data.pop('demographics', None)
        addresses_data = validated_data.pop('addresses', None)
        
        # Update patient fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update demographics if provided
        if demographics_data and hasattr(instance, 'demographics'):
            demographics = instance.demographics
            for attr, value in demographics_data.items():
                setattr(demographics, attr, value)
            demographics.save()
        elif demographics_data:
            PatientDemographics.objects.create(patient=instance, **demographics_data)
        
        # Update addresses if provided
        if addresses_data is not None:
            instance.addresses.all().delete()  # Remove existing addresses
            for address_data in addresses_data:
                PatientAddress.objects.create(patient=instance, **address_data)
        
        return instance

# Optional: Create a simplified serializer for list views
class PatientListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = [
            'id', 'first_name', 'last_name', 'date_of_birth',
            'email', 'phone_primary', 'is_active'
        ]