from django.test import TestCase

from django.test import TestCase
from django.core.management import call_command
from django.contrib.auth.models import Permission
from .models import StaffRole

class StaffRolesSetupTest(TestCase):
    def setUp(self):
        call_command('setup_staff_roles')

    def test_roles_created(self):
        expected_roles = ['DOCTOR', 'HEAD_DOCTOR', 'NURSE', 'HEAD_NURSE', 
                         'RECEPTIONIST', 'LAB_TECHNICIAN', 'PHARMACIST']
        actual_roles = StaffRole.objects.values_list('code', flat=True)
        self.assertEqual(set(expected_roles), set(actual_roles))

    def test_doctor_permissions(self):
        doctor_role = StaffRole.objects.get(code='DOCTOR')
        permissions = set(doctor_role.permissions.values_list('codename', flat=True))
        
        expected_permissions = {
            'view_patient', 'add_patient', 'change_patient',
            'view_patientdemographics', 'add_patientdemographics', 
            'change_patientdemographics',
            'view_patientaddress'
        }
        self.assertEqual(expected_permissions, permissions)

    def test_head_doctor_permissions(self):
        head_doctor_role = StaffRole.objects.get(code='HEAD_DOCTOR')
        permissions = set(head_doctor_role.permissions.values_list('codename', flat=True))
        
        # Head doctor should have all doctor permissions plus delete
        self.assertTrue('delete_patient' in permissions)
        self.assertTrue('delete_patientdemographics' in permissions)
