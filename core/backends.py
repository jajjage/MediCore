from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db import connection
from django_tenants.utils import get_public_schema_name
from apps.staff.models import StaffMember
import logging

logger = logging.getLogger(__name__)

class MultiSchemaModelBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        logger.info(f"Authentication attempt - Schema: {connection.schema_name}")
        logger.info(f"Request data: {request.data if hasattr(request, 'data') else 'No data'}")
        
        # Handle empty username cases
        if not username and hasattr(request, 'data'):
            username = request.data.get('email')
            
        if not username or not password:
            logger.error("Missing credentials - username or password is None")
            return None

        logger.info(f"Attempting authentication for email: {username}")

        if connection.schema_name == get_public_schema_name():
            UserModel = get_user_model()
            try:
                user = UserModel.objects.get(email=username)
                if user.check_password(password):
                    return user
            except UserModel.DoesNotExist:
                logger.warning(f"User {username} not found in public schema")
                return None
        else:
            try:
                user = StaffMember.objects.get(email=username)
                if user.check_password(password):
                    return user
            except StaffMember.DoesNotExist:
                logger.warning(f"User {username} not found in tenant schema")
                return None
        return None

    def get_user(self, user_id):
        UserModel = StaffMember if connection.schema_name != get_public_schema_name() else get_user_model()
        try:
            return UserModel.objects.get(pk=user_id)
        except UserModel.DoesNotExist:
            return None