import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.core.cache import cache
from django.db import connection

from tenants.models import Client

logger = logging.getLogger(__name__)

class TenantAuthBackend(ModelBackend):
    def authenticate(self, request, email=None, password=None, **kwargs):
        subdomain = self.get_subdomain(request)
        schema_name = connection.schema_name
        domain = None

        if not subdomain:
            return None

        # Check cached domains first
        cached_domains = cache.get("active_subdomains_dict") or {}
        if schema_name in cached_domains:
            domain = cached_domains[schema_name]
        else:
            try:
                schema = Client.objects.get(schema_name=schema_name)
                client = schema.domains.get(domain=subdomain)
                self._update_domain_cache(client)
                domain = cached_domains[schema_name]
            except Client.DoesNotExist:
                return None

        # Rest of authentication logic
        UserModel = get_user_model()
        try:
            user = UserModel.objects.get(email=email)
        except UserModel.DoesNotExist:
            return None

        if user.check_password(password) and user.hospital_memberships_user.first().tenant.domains.all().filter(
            domain=domain
        ).exists():
            return user
        return None

    def _update_domain_cache(self, client):
        """Update cache with new domain entry."""
        print("ddd")
        cached_domains = cache.get("active_subdomains_dict") or {}
        cached_domains[client.tenant.schema_name] = client.domain
        cache.set("active_subdomains_dict", cached_domains, timeout=3600)

    def get_subdomain(self, request):
        n = 2
        host = request.get_host().split(":")[0]
        domain_parts = host.lower()
        if len(domain_parts) >= n and settings.BASE_DOMAIN in host:
            return domain_parts
        return None


