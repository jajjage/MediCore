import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db import connection
from django_tenants.utils import get_public_schema_name

from apps.staff.models import StaffMember

logger = logging.getLogger(__name__)


class MultiSchemaModelBackend(ModelBackend):
    """Check to authenticate users in both public and tenant schemas."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        logger.info("Authentication attempt - Schema: %s", connection.schema_name)
        logger.info(
            "Request data: %s", request.data if hasattr(request, "data") else "No data"
        )

        # Handle empty username cases
        if not username and hasattr(request, "data"):
            username = request.data.get("email")

        if not username or not password:
            logger.error("Missing credentials - username or password is None")
            return None

        logger.info("Attempting authentication for email: %s", username)

        # Authenticate user IF schema is public
        if connection.schema_name == get_public_schema_name():
            usermodel = get_user_model()
            try:
                user = usermodel.objects.get(email=username)
                if user.check_password(password):
                    return user
            except usermodel.DoesNotExist:
                logger.warning("User %s, {username} not found in public schema")
                return None
        else:
            # Authenticate user IF schema is tenant
            try:
                user = StaffMember.objects.get(email=username)
                if user.check_password(password):
                    return user
            except StaffMember.DoesNotExist:
                logger.warning("User %s, {username} not found in tenant schema")
                return None
        return None

    # This would be use to get the user from the token later
    def get_user(self, user_id):
        usermodel = (
            StaffMember
            if connection.schema_name != get_public_schema_name()
            else get_user_model()
        )
        try:
            return usermodel.objects.get(pk=user_id)
        except usermodel.DoesNotExist:
            return None
