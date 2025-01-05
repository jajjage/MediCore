from rest_framework import serializers


def check_model_permissions(serializer, data, is_update):
    """
    Check permissions for all related models in patient data.

    Args:
        serializer: The serializer instance
        data: The validated data dictionary
        is_update: Boolean indicating if this is an update operation

    Raises:
        serializers.ValidationError: If permissions are not met.

    """
    # Define permission mapping for all models
    model_permissions = {
        "patient": {"base": True},  # Base patient model
        "patientdemographics": {"field": "demographics"},
        "patientemergencycontact": {"field": "emergency_contact"},
        "patientallergy": {"field": "allergies"},
        "patientchroniccondition": {"field": "chronic_conditions"},
        "patientaddress": {"field": "addresses"},
        "patientmedicalreport": {"field": "medical_reports"},
    }

    # Check base patient permissions
    if is_update and not serializer.check_permission("change", "patient"):
        raise serializers.ValidationError(
            {"error": "You don't have permission to update patient information"}
        )
    if not is_update and not serializer.check_permission("add", "patient"):
        raise serializers.ValidationError(
            {"error": "You don't have permission to create patients"}
        )

    # Check permissions for each related model
    for model_name, config in model_permissions.items():
        if model_name == "patient":
            continue  # Already checked above
        field_name = config["field"]
        if field_name in data:
            if is_update and not serializer.check_permission("change", model_name):
                raise serializers.ValidationError(
                    {field_name: f"You don't have permission to update {model_name}"}
                )
            if not is_update and not serializer.check_permission("add", model_name):
                raise serializers.ValidationError(
                    {field_name: f"You don't have permission to add {model_name}"}
                )

    return data
