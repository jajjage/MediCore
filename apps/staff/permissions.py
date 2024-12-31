from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from .models import StaffMember, StaffRole


def create_default_roles_and_permissions():
    # Create default roles
    doctor_role, _ = StaffRole.objects.get_or_create(name="Doctor")
    nurse_role, _ = StaffRole.objects.get_or_create(name="Nurse")
    receptionist_role, _ = StaffRole.objects.get_or_create(name="Receptionist")
    other_role, _ = StaffRole.objects.get_or_create(name="Other Staff")

    # Define permissions for each model
    patient_permissions = [
        ("view_patient", "Can view patient"),
        ("add_patient", "Can add patient"),
        ("change_patient", "Can change patient"),
        ("delete_patient", "Can delete patient"),
    ]

    appointment_permissions = [
        ("view_appointment", "Can view appointment"),
        ("add_appointment", "Can add appointment"),
        ("change_appointment", "Can change appointment"),
        ("delete_appointment", "Can delete appointment"),
    ]

    medical_record_permissions = [
        ("view_medicalrecord", "Can view medical record"),
        ("add_medicalrecord", "Can add medical record"),
        ("change_medicalrecord", "Can change medical record"),
    ]

    prescription_permissions = [
        ("view_prescription", "Can view prescription"),
        ("add_prescription", "Can add prescription"),
        ("change_prescription", "Can change prescription"),
    ]

    # Assign permissions to roles
    # Doctor permissions
    doctor_perms = (
        patient_permissions
        + appointment_permissions
        + medical_record_permissions
        + prescription_permissions
    )

    # Nurse permissions
    nurse_perms = [
        ("view_patient", "Can view patient"),
        ("view_appointment", "Can view appointment"),
        ("add_appointment", "Can add appointment"),
        ("view_medicalrecord", "Can view medical record"),
        ("add_medicalrecord", "Can add medical record"),
        ("view_prescription", "Can view prescription"),
    ]

    # Receptionist permissions
    receptionist_perms = [
        ("view_patient", "Can view patient"),
        ("add_patient", "Can add patient"),
        ("view_appointment", "Can view appointment"),
        ("add_appointment", "Can add appointment"),
        ("change_appointment", "Can change appointment"),
    ]

    # Other staff permissions
    other_perms = [
        ("view_patient", "Can view patient"),
        ("view_appointment", "Can view appointment"),
    ]

    # Create and assign permissions
    for role, perms in [
        (doctor_role, doctor_perms),
        (nurse_role, nurse_perms),
        (receptionist_role, receptionist_perms),
        (other_role, other_perms),
    ]:
        for codename, name in perms:
            content_type = ContentType.objects.get_for_model(StaffMember)
            permission, _ = Permission.objects.get_or_create(
                codename=codename,
                name=name,
                content_type=content_type,
            )
            role.permissions.add(permission)
