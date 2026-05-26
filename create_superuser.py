import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()

email = os.environ.get('SUPERUSER_EMAIL', 'aciusjob1@gmail.com')
password = os.environ.get('SUPERUSER_PASSWORD', 'Bubabi2026!')

if not User.objects.filter(email=email).exists():
    User.objects.create_superuser(email=email, password=password)
    print(f"✅ Superuser created: {email}")
else:
    print(f"⚠️ Superuser already exists: {email}")
