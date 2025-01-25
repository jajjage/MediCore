import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.core.cache import cache
from django.db import connection

from tenants.models import Client

logger = logging.getLogger(__name__)

class TenantAuthBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        subdomain = self.get_subdomain(request)


        if not username and hasattr(request, "data"):
            username = request.data.get("email")

        if not username or not password:
            logger.error("Missing credentials - username or password is None")
            return None

        if not subdomain:
            return None

        # Check cached domains first
        domain = self.get_tenant_domain(subdomain)
        # Rest of authentication logic
        UserModel = get_user_model()
        try:
            user = UserModel.objects.get(email=username)
        except UserModel.DoesNotExist:
            return None

        if (
            user.check_password(password)
            and user.hospital_memberships_user.exists()
            and user.hospital_memberships_user.first().tenant.domains.filter(domain=domain).exists()
        ):
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

    def get_tenant_domain(self, subdomain):
        """
        Retrieve the tenant domain associated with the given subdomain.
        """
        cached_domains = cache.get("active_subdomains_dict") or {}
        schema_name = connection.schema_name

        if schema_name in cached_domains:
            return cached_domains[schema_name]

        # If not cached, fetch from the database
        try:
            client = Client.objects.get(schema_name=schema_name)
            domain = client.domains.filter(domain=subdomain).first()
            if domain:
                self._update_domain_cache(client, domain)
                return domain.domain
        except Client.DoesNotExist:
            logger.warning(f"Client not found for schema: {schema_name}")

        return None
