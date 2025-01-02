import logging
from datetime import datetime, timezone
from functools import lru_cache
from urllib.parse import urljoin

import jwt  # type: ignore
import requests  # type: ignore
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.core.cache import cache
from django.db import connection
from django.shortcuts import redirect
from django.urls import reverse
from django_tenants.utils import get_public_schema_name
from requests.adapters import HTTPAdapter  # type: ignore
from requests.packages.urllib3.util.retry import Retry  # type: ignore

logger = logging.getLogger(__name__)

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
                    messages.error(request, "Access denied. Please log in to your hospital domain.")
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
        self.refresh_attempt_cache_timeout = 300  # 5 minutes
        self.max_refresh_attempts = 5
        self.session = self._setup_requests_session()
    
    def __call__(self, request):
        try:
            # First check refresh token
            refresh_token = request.COOKIES.get(settings.JWT_AUTH_REFRESH_COOKIE)
            if refresh_token and not self._is_token_blacklisted(refresh_token):
                # Only try to refresh if no valid access token
                access_token = request.COOKIES.get(settings.JWT_AUTH_COOKIE)
                if not access_token:
                    self._refresh_token(request, refresh_token)
            else:
                # No refresh token or blacklisted
                self._clear_auth_cookies(request)

            # Check access token and handle refresh if needed
            if request.COOKIES.get(settings.JWT_AUTH_COOKIE):
                self._handle_token_refresh(request)

        except Exception as e:
            logger.error(f"JWT middleware error: {str(e)}", exc_info=True)
            self._clear_auth_cookies(request)

        response = self.get_response(request)
        self._set_response_cookies(request, response)
        self._set_security_headers(response)
        return response

    def _handle_token_refresh(self, request):
        access_token = request.COOKIES.get(settings.JWT_AUTH_COOKIE)
        if not access_token:
            return

        try:
            payload = self._validate_token(access_token)
            exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
            
            if self._should_refresh_token(exp):
                refresh_token = request.COOKIES.get(settings.JWT_AUTH_REFRESH_COOKIE)
                if refresh_token and not self._is_token_blacklisted(refresh_token):
                    self._refresh_token(request, refresh_token)

        except jwt.ExpiredSignatureError:
            logger.info("Access token expired")
            self._clear_auth_cookies(request)
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {str(e)}")
            self._clear_auth_cookies(request)

    @lru_cache(maxsize=1000)
    def _is_token_blacklisted(self, token):
        """Check if token is blacklisted in cache"""
        return cache.get(f'blacklist_token_{token}', False)

    def _validate_token(self, token):
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=["HS256"],
            options={"verify_exp": True}
        )

    def _should_refresh_token(self, exp_time):
        """Check if token should be refreshed"""
        time_to_expire = (exp_time - datetime.now(timezone.utc)).total_seconds()
        return time_to_expire < settings.JWT_REFRESH_THRESHOLD

    def _refresh_token(self, request, refresh_token):
        """Handle token refresh with rate limiting"""
        cache_key = f'refresh_attempt_{refresh_token}'
        attempts = cache.get(cache_key, 0)

        if attempts >= self.max_refresh_attempts:
            logger.warning(f"Too many refresh attempts for token {attempts}")
            self._clear_auth_cookies(request)
            
            # if refresh_token:
            #     cache.set(cache_key, attempts + 1, self.refresh_attempt_cache_timeout)
            #     url = request.get_host().split(":")[0]
            #     tenant_domain = url.split(".")[0]
            #     new_tokens = self._get_new_tokens(tenant_domain, refresh_token)
            #     if new_tokens:
            #         self._update_request_tokens(request, new_tokens)

        cache.set(cache_key, attempts + 1, self.refresh_attempt_cache_timeout)
        url = request.get_host().split(":")[0]
        tenant_domain = url.split(".")[0]
        new_tokens = self._get_new_tokens(tenant_domain, refresh_token)
        if new_tokens:
            self._update_request_tokens(request, new_tokens)

    def _get_new_tokens(self, tenant_domain, refresh_token):
        """Get new tokens from authentication server"""
        try:
            # For local development
            # if settings.DEBUG:
            #     refresh_url = f"http://localhost:8000{settings.API_BASE_PATH}/auth/token/refresh/"
           
            refresh_url = urljoin(
                f"{settings.SITE_SCHEME}://{tenant_domain}.{settings.SITE_DOMAIN}:{settings.LOCAL_PORT}",
                f"{settings.API_BASE_PATH}/auth/token/refresh/"
            )
            
            response = self.session.post(
                refresh_url,
                json={"refresh": refresh_token},
                timeout=settings.API_TIMEOUT,
                verify=not settings.DEBUG
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.RequestException as e:
            logger.error(f"Token refresh failed: {str(e)}")
            return None

        finally:
            self.session.close()

    def _update_request_tokens(self, request, tokens):
        """Update request with new tokens"""
        request.new_jwt = tokens.get('access')
        request.new_refresh = tokens.get('refresh')
        request.COOKIES[settings.JWT_AUTH_COOKIE] = tokens['access']

    def _clear_auth_cookies(self, request):
        """Clear authentication cookies"""
        request.COOKIES.pop(settings.JWT_AUTH_COOKIE, None)
        request.COOKIES.pop(settings.JWT_AUTH_REFRESH_COOKIE, None)
        request.new_jwt = ''
        request.new_refresh = ''

    def _set_response_cookies(self, request, response):
        """Set secure cookies in response"""
        
        # print(f"Adding new token to cookies:{ request.new_jwt}")
        if hasattr(request, 'new_jwt') and request.new_jwt:
            response.set_cookie(
                settings.JWT_AUTH_COOKIE,
                request.new_jwt,
                max_age=settings.JWT_ACCESS_TOKEN_LIFETIME.total_seconds(),
                httponly=True,
                secure=True,
                samesite='Strict'
            )
        if hasattr(request, 'new_refresh') and request.new_refresh:
            response.set_cookie(
                settings.JWT_AUTH_REFRESH_COOKIE,
                request.new_refresh,
                max_age=settings.JWT_REFRESH_TOKEN_LIFETIME.total_seconds(),
                httponly=True,
                secure=True,
                samesite='Strict'
            )

    def _set_security_headers(self, response):
        """Set security headers"""
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'

    def _setup_requests_session(self):
        session = requests.Session()
        retries = Retry(
            total=settings.API_MAX_RETRIES,
            backoff_factor=0.1,
            status_forcelist=[500, 502, 503, 504]
        )
        session.mount('http://', HTTPAdapter(max_retries=retries))
        session.mount('https://', HTTPAdapter(max_retries=retries))
        return session


class DynamicAuthModelMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if connection.schema_name == "public":
            settings.AUTH_USER_MODEL = settings.PUBLIC_SCHEMA_USER_MODEL
        else:
            settings.AUTH_USER_MODEL = settings.TENANT_SCHEMA_USER_MODEL
        return self.get_response(request)


