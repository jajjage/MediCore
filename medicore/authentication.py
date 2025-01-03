import logging

from django.conf import settings
from django.db import connection
from django_tenants.utils import get_public_schema_name
from rest_framework_simplejwt.authentication import JWTAuthentication  # type: ignore
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError  # type: ignore

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
                logger.error(f"Token validation failed: {str(e)}")
                raise InvalidToken(str(e))
            except Exception as e:
                logger.error(f"Unexpected error during token validation: {str(e)}")
                raise TokenError(str(e))

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
                else:
                    if not user._meta.model.__name__ == "StaffMember":
                        raise TokenError("Invalid user type for tenant schema")

                return user, validated_token

            except Exception as e:
                logger.error(f"Error getting user from token: {str(e)}")
                raise TokenError(str(e))

        except Exception as e:
            logger.error(f"Authentication failed: {str(e)}")
            return None
