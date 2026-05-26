import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()

email = os.environ.get('SUPERUSER_EMAIL', 'aciusjob1@gmail.com')
password = os.environ.get('SUPERUSER_PASSWORD', 'Bubabi2026!')

user, created = User.objects.get_or_create(email=email, defaults={'password': password})

if created:
    user.set_password(password)
    user.is_superuser = True
    user.is_staff = True
    user.status = 'active'  # ← THIS IS THE FIX
    user.has_accepted_terms = True
    user.save()
    print(f"✅ Superuser created: {email}")
else:
    # Update existing user too
    user.set_password(password)
    user.is_superuser = True
    user.is_staff = True
    user.status = 'active'
    user.has_accepted_terms = True
    user.save()
    print(f"✅ Superuser updated: {email}")
