from django.db import transaction

from apps.staff.models import Department, DepartmentMember, StaffTransfer


class StaffManagementService:
    @staticmethod
    def process_transfer(transfer_data):
        """Handle the complete transfer process."""
        with transaction.atomic():
            # Create transfer record
            transfer = StaffTransfer.objects.create(**transfer_data)

            # Update department assignments
            DepartmentMember.objects.filter(
                id=transfer.from_assignment.id
            ).update(is_active=False)

            # Create new department assignment
            DepartmentMember.objects.create(
                user=transfer.from_assignment.user,
                department=transfer.to_assignment.department,
                role=transfer.from_assignment.role,
                start_date=transfer.effective_date
            )

            return transfer

    @staticmethod
    def validate_staffing_levels(department_id):
        """Validate department staffing levels."""
        department = Department.objects.get(id=department_id)
        current_staff = department.get_active_staff().count()
        required_staff = department.min_staff_required

        return {
            "status": current_staff >= required_staff,
            "current_staff": current_staff,
            "required_staff": required_staff,
            "shortage": max(0, required_staff - current_staff)
        }
