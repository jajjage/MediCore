from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Initializes database schema for new tenants"

    def add_arguments(self, parser):
        parser.add_argument("--schema", type=str, help="Tenant schema name")

    def handle(self, *args, **options):
        current_schema = options["schema"]
        if not current_schema:
            self.stdout.write(self.style.ERROR("Schema name is required"))
            return

        try:
            with connection.cursor() as cursor:
                # Switch to tenant schema
                cursor.execute(f"SET search_path TO {current_schema}")

                # Create sequences
                self.create_sequences(cursor)

                # Create indexes
                self.create_indexes(cursor)

            self.stdout.write(
                self.style.SUCCESS(
                    f"Tenant setup completed successfully for schema: {current_schema}"
                )
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error during tenant setup: {e!s}")
            )
            raise

    def create_sequences(self, cursor):
        """Create tenant-specific sequences."""
        cursor.execute("""
            CREATE SEQUENCE IF NOT EXISTS patient_pin_seq_middle
            START WITH 20
            INCREMENT BY 1
            MINVALUE 20
            MAXVALUE 99999
            CYCLE;
        """)

        cursor.execute("""
            CREATE SEQUENCE IF NOT EXISTS patient_pin_seq_last
            START WITH 40
            INCREMENT BY 1
            MINVALUE 40
            MAXVALUE 99999
            CYCLE;
        """)

    def create_indexes(self, cursor):
        """Create tenant-specific indexes."""
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS patient_pin_lower_idx ON patients (LOWER(pin));"
        )
