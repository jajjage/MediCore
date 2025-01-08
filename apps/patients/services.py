from django.db import transaction


class AppointmentService:
    @staticmethod
    @transaction.atomic
    def create_appointment(serializer, user, patient_id):
        """
        Create a new appointment.
        """
        return serializer.save(
            created_by=user,
            modified_by=user,
            physician=user,
            patient_id=patient_id
        )

    @staticmethod
    @transaction.atomic
    def update_appointment(serializer, user):
        """
        Update an existing appointment.
        """
        return serializer.save(
            modified_by=user,
            physician=user
        )

class OperationService:
    @staticmethod
    @transaction.atomic
    def create_operation(serializer, user, patient_id):
        """
        Create a new appointment.
        """
        return serializer.save(
            surgeon=user,
            patient_id=patient_id
        )

    @staticmethod
    @transaction.atomic
    def update_operation(serializer, user):
        """
        Update an existing appointment.
        """
        return serializer.save(
            modified_by=user,
            surgeon=user
        )

