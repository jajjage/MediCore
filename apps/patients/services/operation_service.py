from django.db import transaction


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

