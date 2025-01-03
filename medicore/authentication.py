import logging

from django.conf import settings
from django.db import connection
from django_tenants.utils import get_public_schema_name
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

logger = logging.getLogger(__name__)


class RobustCookieJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        try:
            # Get token from cookie
            raw_token = request.COOKIES.get(settings.JWT_AUTH_COOKIE)
            if not raw_token:
                logger.warning("No token found in cookies")
                return None

            # Validate token
            try:
                validated_token = self.get_validated_token(raw_token)
            except TokenError as e:
                logger.exception("Token validation failed: %s", e)
                raise InvalidToken(str(e)) from e
            except Exception as e:
                logger.exception("Unexpected error during token validation: %s", e)
                raise TokenError(str(e)) from e

            # Get user based on schema
            try:
                user = self.get_user(validated_token)
                if not user:
                    logger.warning("User not found for token")
                    raise TokenError("User not found")

                # Validate user for current schema
                schema_name = connection.schema_name

                if schema_name == get_public_schema_name():
                    if not user._meta.model.__name__ == "MyUser":
                        raise TokenError("Invalid user type for public schema")
                elif user._meta.model.__name__ != "StaffMember":
                    raise TokenError("Invalid user type for tenant schema")

                return user, validated_token  # noqa: TRY300

            except Exception as e:
                logger.exception("Error getting user from token: %s", e)
                raise TokenError(str(e)) from e

        except (TokenError, InvalidToken) as e:
            logger.exception("Authentication failed: %s", e)
            return None
