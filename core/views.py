import logging

from django.conf import settings
from django.contrib.auth.models import update_last_login
from django.core.cache import cache
from jsonschema import ValidationError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

logger = logging.getLogger(__name__)

class CookieTokenObtainPairView(TokenObtainPairView):
    def post(self, request, *args, **kwargs):
        try:
            response = super().post(request, *args, **kwargs)
            if response.status_code == status.HTTP_200_OK:
                user = self.get_user(request)
                if user:
                    update_last_login(None, user)
                    return self.set_token_cookies(response)
            return response
        except (TokenError, ValidationError) as e:
            logger.exception("Token generation failed: %s", e)
            return Response(
                {"error": "Authentication failed"}, status=status.HTTP_401_UNAUTHORIZED
            )
    def get_user(self, request):
        """
        Retrieve the user object from the validated token or serializer data.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return serializer.user

    def _validate_token_data(self, data):
        if "access" not in data or "refresh" not in data:
            raise ValueError("Token data missing from response")

    def set_token_cookies(self, response):
        try:
            logger.debug(f"Setting cookies with data: {response.data}")
            self._validate_token_data(response.data)
            # Set access token cookie
            response.set_cookie(
                settings.JWT_AUTH_COOKIE,
                response.data["access"],
                max_age=settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds(),
                secure=settings.JWT_AUTH_SECURE,
                httponly=settings.JWT_AUTH_HTTPONLY,
                samesite=settings.JWT_AUTH_SAMESITE,
                path=settings.JWT_AUTH_PATH,
            )

            # Set refresh token cookie
            response.set_cookie(
                settings.JWT_AUTH_REFRESH_COOKIE,
                response.data["refresh"],
                max_age=settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds(),
                secure=settings.JWT_AUTH_SECURE,
                httponly=settings.JWT_AUTH_HTTPONLY,
                samesite=settings.JWT_AUTH_SAMESITE,
                path=settings.JWT_AUTH_PATH,
            )

            # Remove tokens from response data for security
            response.data.pop("access")
            response.data.pop("refresh")
            logger.info("Cookies set successfully")
            return response

        except Exception as e:
            logger.exception("Failed to set cookies: %s", e)
            return Response(
                {"error": "Failed to set authentication cookies"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class CookieTokenRefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        refresh_token = request.COOKIES.get(settings.JWT_AUTH_REFRESH_COOKIE)

        if not refresh_token:
            return Response(
                {"detail": "No refresh token found"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if self._is_token_blacklisted(refresh_token):
            return Response(
                {"detail": "Token is blacklisted"}, status=status.HTTP_401_UNAUTHORIZED
            )

        try:
            # Rate limiting check
            if not self._check_rate_limit(refresh_token):
                return Response(
                    {"detail": "Too many refresh attempts"},
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )

            # Validate and get new tokens
            request._full_data = {"refresh": refresh_token}
            response = super().post(request, *args, **kwargs)

            if response.status_code == status.HTTP_200_OK:
                self._set_token_cookies(response)
                return response

        except TokenError as e:
            return Response({"detail": str(e)}, status=status.HTTP_401_UNAUTHORIZED)
        except Exception as e:
            logger.error("Token refresh error: %s", e, exc_info=True)  # noqa: G201
            return Response(
                {"detail": "Token refresh failed"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _is_token_blacklisted(self, token, cache_timeout=300):
        cache_key = f"blacklist_token_{token}"
        return cache.get(cache_key, False)

    def _check_rate_limit(self, token, max_attempts=5, timeout=300):
        cache_key = f"refresh_attempt_{token}"
        attempts = cache.get(cache_key, 0)

        if attempts >= max_attempts:
            return False

        cache.set(cache_key, attempts + 1, timeout)
        return True

    def _set_token_cookies(self, response):
        if "access" in response.data:
            response.set_cookie(
                settings.JWT_AUTH_COOKIE,
                response.data["access"],
                max_age=settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds(),
                httponly=settings.JWT_AUTH_HTTPONLY,
                secure=settings.JWT_AUTH_SECURE,
                samesite=settings.JWT_AUTH_SAMESITE,
                path=settings.JWT_AUTH_PATH,
            )
            response.data.pop("access")

        if "refresh" in response.data:
            response.set_cookie(
                settings.JWT_AUTH_REFRESH_COOKIE,
                response.data["refresh"],
                max_age=settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds(),
                httponly=settings.JWT_AUTH_HTTPONLY,
                secure=settings.JWT_AUTH_SECURE,
                samesite=settings.JWT_AUTH_SAMESITE,
                path=settings.JWT_AUTH_PATH,
            )
            response.data.pop("refresh")


class CookieTokenVerifyView(TokenVerifyView):
    def post(self, request, *args, **kwargs):
        token = request.COOKIES.get(settings.JWT_AUTH_COOKIE)

        if not token:
            return Response(
                {"error": "No token found"}, status=status.HTTP_401_UNAUTHORIZED
            )

        try:
            request.data["token"] = token
            return super().post(request, *args, **kwargs)
        except InvalidToken as e:
            logger.exception("Token verification error: %s", e)
            return Response(
                {"error": "Invalid token"}, status=status.HTTP_401_UNAUTHORIZED
            )


class LogoutView(APIView):
    def post(self, request, *args, **kwargs):
        try:
            response = Response({"detail": "Successfully logged out."})
            response.delete_cookie(settings.JWT_AUTH_COOKIE)
            response.delete_cookie(settings.JWT_AUTH_REFRESH_COOKIE)
            return response
        except Exception as e:
            logger.error("Logout error: %s", e, exc_info=True)  # noqa: G201
            return Response(
                {"error": "Logout failed"}, status=status.HTTP_400_BAD_REQUEST
            )
