# core/middleware.py
from django.contrib.auth import logout
from django.db import connection
from django.shortcuts import redirect
from django.urls import reverse
from django_tenants.utils import get_public_schema_name
from django.contrib import messages
from django.utils.functional import SimpleLazyObject
from django.conf import settings
import jwt # type: ignore
from datetime import datetime, timezone
from .exceptions import TokenError


class AdminAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/admin/"):
            user = request.user

            # If not authenticated, allow normal login flow
            if not user.is_authenticated:
                return self.get_response(request)

            current_schema = connection.schema_name

            if current_schema == get_public_schema_name():
                # On main domain
                if not user.is_superuser:
                    messages.error(
                        request, "Access denied. Please log in to your hospital domain."
                    )
                    logout(request)
                    return redirect(reverse("admin:login"))
            else:
                # On tenant domain
                if not user.hospital or user.hospital.schema_name != current_schema:
                    messages.error(
                        request,
                        "Access denied. Please log in to your assigned hospital domain.",
                    )
                    logout(request)
                    return redirect(reverse("admin:login"))

        return self.get_response(request)


class JWTRefreshMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            access_token = request.COOKIES.get(settings.JWT_AUTH_COOKIE)
            if access_token:
                payload = jwt.decode(
                    access_token,
                    settings.SECRET_KEY,
                    algorithms=['HS256']
                )
                exp = datetime.fromtimestamp(payload['exp'], tz=timezone.utc)
                
                # If token is about to expire (less than 5 minutes)
                if (exp - datetime.now(timezone.utc)).total_seconds() < 300:
                    refresh_token = request.COOKIES.get(settings.JWT_AUTH_REFRESH_COOKIE)
                    if refresh_token:
                        # Implement token refresh logic here
                        pass

        except jwt.ExpiredSignatureError:
            # Handle expired token
            pass
        except jwt.InvalidTokenError:
            # Handle invalid token
            pass
        except Exception as e:
            # Log unexpected errors
            pass

        response = self.get_response(request)
        return response
