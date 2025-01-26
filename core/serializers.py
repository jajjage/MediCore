from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import Token

from .models import HospitalMembership

User = get_user_model()
class CustomTokenObtainSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user) -> Token:
        token = super().get_token(user)  # Generates default token

        # Add custom claims to the JWT payload
        memberships = HospitalMembership.objects.filter(user=user).select_related("role")
        token["roles"] = [
            membership.role.code if membership.role and membership.role.name else "UNKNOWN"
            for membership in memberships
        ]

        token["primary_role"] = memberships.first().role.name if memberships.exists() else None

        return token

    def validate(self, attrs):
        data = super().validate(attrs)  # Returns default tokens (access + refresh)

        # Add user data to the login response
        data["user"] = {
            "id": self.user.id,
            "email": self.user.email,
            "roles": [membership.role.name for membership in self.user.hospital_memberships_user.all()]
        }
        return data


class AdminUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            "email",
            "password",
        ]

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("This email is already registered.")
        return value.lower()
