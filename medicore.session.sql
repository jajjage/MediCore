 def has_object_permission(self, request, view, obj):
        # Additional object-level permissions for appointments
        user_role = str(request.user.role).strip().upper().replace(" ", "_")

        # Doctors can only modify their own appointments
        if user_role == "DOCTOR":
            return obj.physician == request.user

        # Nurses can view all appointments but only modify appointments in their department
        if user_role == "NURSE":
            if request.method in ["PUT", "PATCH", "DELETE"]:
                return request.user.departmentmember_set.filter(
                    department=obj.department
                ).exists()
            return True

        # Receptionists and Admins can modify all appointments
        return user_role in ["RECEPTIONIST", "ADMIN"]