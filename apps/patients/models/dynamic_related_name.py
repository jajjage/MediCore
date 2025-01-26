import uuid

from django.db import models
from django.db.models.base import ModelBase


class BaseModelMeta(ModelBase):
    def __new__(cls, name, bases, attrs):
        # Let Django's ModelBase create the class first
        new_class = super().__new__(cls, name, bases, attrs)

        # Process only concrete (non-abstract) models
        if not new_class._meta.abstract:
            # Find the 'patient' ForeignKey field
            for field in new_class._meta.fields:
                if field.name == "patient" and isinstance(field, models.ForeignKey):
                    # Generate the dynamic related_name
                    subclass_name = name.lower().replace("patient", "")
                    related_name = f"{subclass_name}s"  # Pluralize
                    field.remote_field.related_name = related_name
        return new_class
