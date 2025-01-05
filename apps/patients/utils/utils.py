from django.db.models import Q


class SearchQueryOptimizer:
    """
    Utility class to handle search query optimization.
    """

    @staticmethod
    def clean_query(query):
        return query.strip().lower()

    @staticmethod
    def build_search_filters(query):
        """
        Build optimized search filters based on query type.
        """
        if query.replace("-", "").isdigit():
            # If query looks like a PIN or phone number
            return Q(pin__icontains=query) | Q(phone_primary__icontains=query)
        if "@" in query:
            # If query looks like an email
            return Q(email__icontains=query)
        # Default to name search
        return Q(first_name__icontains=query) | Q(last_name__icontains=query)


class OptimizedQueryMixin:
    """Mixin for optimizing database queries."""

    def get_queryset(self):
        return self.queryset.select_related(
            "demographics", "emergency_contact"
        ).prefetch_related(
            "allergies", "chronic_conditions", "addresses", "medical_reports"
        )
