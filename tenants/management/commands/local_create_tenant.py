# tenants/management/commands/create_tenant.py

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context
from tenants.models import Client, Domain, HospitalProfile
from datetime import datetime, timedelta
import uuid

User = get_user_model()

class Command(BaseCommand):
    help = 'Creates a new tenant with admin user and domain'

    def add_arguments(self, parser):
        # Tenant arguments
        parser.add_argument('--schema_name', type=str, help='Schema name (optional, will be auto-generated if not provided)')
        parser.add_argument('--name', required=True, type=str, help='Hospital name')
        
        # Domain arguments
        parser.add_argument('--domain-domain', required=True, type=str, help='Domain name for the tenant')
        
        # Hospital Profile arguments
        parser.add_argument('--admin-email', required=True, type=str, help='Admin user email')
        parser.add_argument('--admin-password', required=True, type=str, help='Admin user password')
        parser.add_argument('--subscription-plan', type=str, 
                          choices=['trial', 'basic', 'premium'], 
                          default='trial',
                          help='Subscription plan type')

    def handle(self, *args, **options):
        schema_name = options.get('schema_name') or f"client_{uuid.uuid4().hex[:8]}"
        
        # Create the tenant
        tenant = Client(
            schema_name=schema_name,
            name=options['name'],
            paid_until=datetime.now() + timedelta(days=30),
            on_trial=options['subscription_plan'] == 'trial'
        )
        
        try:
            tenant.save()
            self.stdout.write(self.style.SUCCESS(f'Created tenant: {tenant.name}'))

            # Add domain for tenant
            domain = Domain.objects.create(
                domain=options['domain_domain'],
                tenant=tenant,
                is_primary=True
            )
            self.stdout.write(self.style.SUCCESS(f'Created domain: {domain.domain}'))

            # Create admin user and hospital profile
            with schema_context(tenant.schema_name):
                admin_user = User.objects.create_superuser(
                    username=options['admin_email'],
                    email=options['admin_email'],
                    password=options['admin_password'],
                    first_name='Hospital',
                    last_name='Admin'
                )
                self.stdout.write(self.style.SUCCESS(f'Created admin user: {admin_user.email}'))

                hospital_profile = HospitalProfile.objects.create(
                    tenant=tenant,
                    admin_user=admin_user,
                    subscription_plan=options['subscription_plan'],
                    hospital_name=options['name'],
                    contact_email=options['admin_email']
                )
                self.stdout.write(
                    self.style.SUCCESS(f'Created hospital profile for: {hospital_profile.hospital_name}')
                )

            self.stdout.write(
                self.style.SUCCESS(
                    f'\nSuccessfully created new hospital tenant:\n'
                    f'Name: {options["name"]}\n'
                    f'Schema: {schema_name}\n'
                    f'Domain: {options["domain_domain"]}\n'
                    f'Admin Email: {options["admin_email"]}\n'
                    f'Subscription Plan: {options["subscription_plan"]}'
                )
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating tenant: {str(e)}')
            )
            raise