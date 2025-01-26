import logging

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django_tenants.utils import schema_context

from apps.patients.models.core import Patient
from hospital.models import HospitalMembership

logger = logging.getLogger(__name__)

@receiver(post_save, sender=HospitalMembership)
def create_patient_profile(sender, instance, created, **kwargs):
    code_lenght = 4
    try:
        if instance.role.name == "Patient":
            user = instance.user

            # Validate hospital profile exists
            try:
                hospital_profile = instance.tenant.hospital_profile
                hospital_code = hospital_profile.hospital_code

                # Validate hospital code
                if not hospital_code or len(hospital_code) < code_lenght:
                    raise ValidationError("Invalid hospital code")

            except (AttributeError, ValidationError) as e:
                logger.exception(f"Hospital code validation error: {e}")
                return

            # Atomic transaction to ensure consistency
            with schema_context(instance.tenant.schema_name), transaction.atomic():
                    patient, is_new = Patient.objects.get_or_create(user=user)

                    if is_new:
                        try:
                            patient.generate_pin(hospital_code)
                            patient.save()

                            # Optional: Send notification
                            # send_patient_registration_notification(patient)

                            logger.info(f"Patient profile created for user {user.id}")

                        except Exception as e:
                            logger.exception(f"Error creating patient profile: {e}")
                            transaction.set_rollback(True)

    except (ValidationError, AttributeError, transaction.TransactionManagementError) as unexpected_error:
        logger.critical(f"Specific error in patient profile creation: {unexpected_error}")


@receiver([post_save, post_delete], sender=HospitalMembership)
def clear_staff_cache(sender, instance, **kwargs):
    cache.delete(f"hospital_{instance.hospital_profile.id}_members")
