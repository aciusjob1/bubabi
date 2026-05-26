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

# Also assign Leader role if not already assigned
from apps.governance.models import Role, MemberRole
try:
    leader_role = Role.objects.get(name='Leader')
    if not MemberRole.objects.filter(member=user, role=leader_role).exists():
        MemberRole.objects.create(member=user, role=leader_role)
        print(f"✅ Leader role assigned to {email}")
except Exception as e:
    print(f"⚠️ Could not assign Leader role: {e}")
