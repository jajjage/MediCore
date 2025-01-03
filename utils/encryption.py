# utils/encryption.py

from cryptography.fernet import Fernet
from django.conf import settings
from functools import wraps


class FieldEncryption:
    def __init__(self):
        self.fernet = Fernet(settings.ENCRYPTION_KEY)

    def encrypt(self, text):
        if not text:
            return text
        return self.fernet.encrypt(text.encode()).decode()

    def decrypt(self, encrypted_text):
        if not encrypted_text:
            return encrypted_text
        return self.fernet.decrypt(encrypted_text.encode()).decode()


# Create a singleton instance
field_encryption = FieldEncryption()


# Decorator for model methods that need encryption
def encrypt_sensitive_fields(fields):
    def decorator(func):
        @wraps(func)
        def wrapper(instance, *args, **kwargs):
            # Encrypt specified fields before save
            for field in fields:
                value = getattr(instance, field, None)
                if value:
                    setattr(
                        instance, f"{field}_encrypted", field_encryption.encrypt(value)
                    )
                    setattr(instance, field, None)  # Clear the plain text value
            return func(instance, *args, **kwargs)

        return wrapper

    return decorator
