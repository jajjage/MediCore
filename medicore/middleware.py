import logging

from django.conf import settings
from django.core.cache import cache
from django.db import connection

from tenants.models import Client

logger = logging.getLogger(__name__)

class SubdomainTenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.main_domain = settings.BASE_DOMAIN

    def __call__(self, request):
        host = request.get_host().split(":")[0].lower()
        schema_name = connection.schema_name

        if self.main_domain in host:
            subdomain = host.lower()

            # Check cache first
            cached_domains = cache.get("active_subdomains_dict") or {}

            print(cached_domains)
            if schema_name in cached_domains:
                subdomain = cached_domains[schema_name]
            else:
                try:
                    schema = Client.objects.get(schema_name=schema_name)
                    client = schema.domains.get(domain=subdomain)
                    self._update_cache(client)
                except Client.DoesNotExist:
                    request.tenant = None
        else:
            request.tenant = None

        return self.get_response(request)

    def _update_cache(self, client):
        cached_domains = cache.get("active_subdomains_dict") or {}
        cached_domains[client.tenant.schema_name] = client.domain
        cache.set("active_subdomains_dict", cached_domains, timeout=3600)
