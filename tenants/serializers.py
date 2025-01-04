from rest_framework import serializers

from .models import Client


class TenantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = ["schema_name", "name", "paid_until", "on_trial"]

    def validate_schema_name(self, value):
        if Client.objects.filter(schema_name=value).exists():
            raise serializers.ValidationError("This schema name is already in use.")
        return value.lower()
