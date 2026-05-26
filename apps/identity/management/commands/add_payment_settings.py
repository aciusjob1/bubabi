from django.core.management.base import BaseCommand
from django.db import models, migrations
import json

class Command(BaseCommand):
    help = 'Add payment_methods JSON field to Clan model'

    def handle(self, *args, **options):
        # Use raw SQL to add JSON field (SQLite compatible as TEXT)
        from django.db import connection
        with connection.cursor() as cursor:
            # Check if column exists
            cursor.execute("PRAGMA table_info(identity_clan)")
            columns = [row[1] for row in cursor.fetchall()]
            
            if 'payment_methods' not in columns:
                cursor.execute("ALTER TABLE identity_clan ADD COLUMN payment_methods TEXT DEFAULT '{}'")
                self.stdout.write(self.style.SUCCESS('✅ Added payment_methods column'))
            else:
                self.stdout.write('✅ payment_methods column already exists')
