from django.core.cache import cache


class CachedPatientSearchMixin:
    """
    Mixin to handle caching for patient searches.
    """

    CACHE_PREFIX = "patient_search"
    CACHE_TIMEOUT = 3600  # 1 hour

    def get_cache_key(self, query):
        return f"{self.CACHE_PREFIX}:{query}"

    def get_cached_results(self, query):
        cache_key = self.get_cache_key(query)
        return cache.get(cache_key)

    def set_cached_results(self, query, results):
        cache_key = self.get_cache_key(query)
        cache.set(cache_key, results, self.CACHE_TIMEOUT)
