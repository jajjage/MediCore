import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import connection
from django_tenants.utils import get_public_schema_name
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

logger = logging.getLogger(__name__)

class RobustCookieJWTAuthentication(JWTAuthentication):
    def get_user_from_model(self, validated_token, user_model):
        """AHelper method to get user from a specific model."""
        try:
            user_id = validated_token[settings.SIMPLE_JWT["USER_ID_CLAIM"]]
            return user_model.objects.get(id=user_id)
        except user_model.DoesNotExist:
            return None
        except Exception as e:
            logger.exception(f"Error getting user from {user_model.__name__}: {e}")
            return None

    def _get_validated_token(self, raw_token):
        try:
            return self.get_validated_token(raw_token)
        except TokenError as e:
            logger.exception("Token validation failed: %s", e)
            raise InvalidToken(str(e)) from e
        except Exception as e:
            logger.exception("Unexpected error during token validation: %s", e)
            raise TokenError(str(e)) from e

    def _get_public_schema_user(self, validated_token):
        user_model = get_user_model()
        user = self.get_user_from_model(validated_token, user_model)
        if not user:
            logger.warning("User not found in public schema")
            raise TokenError("User not found in public schema")
        return user, user_model

    def _get_tenant_schema_user(self, validated_token):
        from django.apps import apps

        from apps.staff.models import StaffMember
        user_model = apps.get_model("core", "MyUser")

        user = self.get_user_from_model(validated_token, StaffMember)
        if not user:
            user = self.get_user_from_model(validated_token, user_model)

        if not user:
            logger.warning("User not found in either StaffMember or MyUser")
            raise TokenError("User not found in tenant schema")

        return user, user_model, StaffMember

    def authenticate(self, request):
        try:
            raw_token = request.COOKIES.get(settings.JWT_AUTH_COOKIE)
            if not raw_token:
                logger.warning("No token found in cookies")
                return None

            validated_token = self._get_validated_token(raw_token)
            schema_name = connection.schema_name
            is_public_schema = schema_name == get_public_schema_name()

            print(f"validated token: {validated_token} schema name: {schema_name} its public_schema:{is_public_schema}")
            if is_public_schema:
                user, user_model = self._get_public_schema_user(validated_token)
                if not isinstance(user, user_model):
                    raise TokenError("Invalid user type for public schema")
            else:
                user, user_model, staffmember = self._get_tenant_schema_user(validated_token)
                if not is_public_schema and isinstance(user, (user_model, staffmember)):
                    cache_key = f"tenant_access_{user.id}_{schema_name}"
                    has_access = cache.get(cache_key)
                    if has_access is None:
                        has_access = user.has_tenant_access(schema_name)
                        cache.set(cache_key, has_access, timeout=300)

                    if not has_access:
                        logger.warning(
                            f"MyUser {user.id} attempted to access unauthorized "
                            f"tenant {schema_name}"
                        )
                        raise TokenError("User not authorized for this tenant")

                    # You might want to add the permission type to the request
                    request.tenant_permission_type = user.get_tenant_permission_type(schema_name)
            return user, validated_token

        except (TokenError, InvalidToken) as e:
            logger.exception("Authentication failed: %s", e)
            return None
