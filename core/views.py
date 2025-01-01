import logging

from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken  # type: ignore
from rest_framework_simplejwt.views import (  # type: ignore
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)  # type: ignore

logger = logging.getLogger(__name__)


class CookieTokenObtainPairView(TokenObtainPairView):
    def post(self, request, *args, **kwargs):
        try:
            response = super().post(request, *args, **kwargs)
            if response.status_code == 200:
                logger.info("Token generation successful")
                return self.set_token_cookies(response)
            return response
        except Exception as e:
            logger.error(f"Token generation failed: {str(e)}")
            return Response({"error": "Authentication failed"}, status=status.HTTP_401_UNAUTHORIZED)

    def set_token_cookies(self, response):
        try:
            logger.debug(f"Setting cookies with data: {response.data}")
            if "access" not in response.data or "refresh" not in response.data:
                raise ValueError("Token data missing from response")

            # Set access token cookie
            response.set_cookie(
                key=settings.JWT_AUTH_COOKIE,
                value=response.data["access"],
                max_age=settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds(),
                secure=settings.JWT_AUTH_SECURE,
                httponly=settings.JWT_AUTH_HTTPONLY,
                samesite=settings.JWT_AUTH_SAMESITE,
                path="/",
            )

            # Set refresh token cookie
            response.set_cookie(
                key=settings.JWT_AUTH_REFRESH_COOKIE,
                value=response.data["refresh"],
                max_age=settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds(),
                secure=settings.JWT_AUTH_SECURE,
                httponly=settings.JWT_AUTH_HTTPONLY,
                samesite=settings.JWT_AUTH_SAMESITE,
                path="/",
            )

            # Remove tokens from response data for security
            response.data = {"detail": "Login successful"}
            logger.info("Cookies set successfully")
            return response

        except Exception as e:
            logger.error(f"Failed to set cookies: {str(e)}")
            return Response(
                {"error": "Failed to set authentication cookies"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class CookieTokenRefreshView(TokenRefreshView):
   pass

class CookieTokenVerifyView(TokenVerifyView):
    def post(self, request, *args, **kwargs):
        token = request.COOKIES.get(settings.JWT_AUTH_COOKIE)

        if not token:
            return Response({"error": "No token found"}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            request.data["token"] = token
            return super().post(request, *args, **kwargs)
        except InvalidToken as e:
            logger.error(f"Token verification error: {str(e)}")
            return Response({"error": "Invalid token"}, status=status.HTTP_401_UNAUTHORIZED)


class LogoutView(APIView):
    def post(self, request, *args, **kwargs):
        try:
            response = Response({"detail": "Successfully logged out."})
            response.delete_cookie(settings.JWT_AUTH_COOKIE)
            response.delete_cookie(settings.JWT_AUTH_REFRESH_COOKIE)
            return response
        except Exception as e:
            logger.error(f"Logout error: {str(e)}")
            return Response({"error": "Logout failed"}, status=status.HTTP_400_BAD_REQUEST)
