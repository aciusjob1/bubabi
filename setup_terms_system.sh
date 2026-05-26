#!/bin/bash
echo "🚀 Installing Terms Acceptance System for BUBABI..."

# =========================
# 1. ADD FIELDS TO MEMBER MODEL
# =========================
echo "🧱 Adding terms fields to Member model..."
sed -i '/accepted_terms_version/a\    accepted_terms_user_agent = models.TextField(blank=True, help_text="Browser/device info when terms accepted")' apps/identity/models.py

# =========================
# 2. CREATE LEGAL CONFIG
# =========================
mkdir -p apps/identity/utils
cat > apps/identity/utils/legal.py << 'LEGAL'
# BUBABI Legal Configuration
CURRENT_TERMS_VERSION = "v1"
CURRENT_PRIVACY_VERSION = "v1"
LEGAL

# =========================
# 3. NETWORK UTIL
# =========================
cat > apps/identity/utils/network.py << 'NET'
def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')
NET

# =========================
# 4. MIDDLEWARE — Enforce terms before any page access
# =========================
echo "🧠 Updating TermsAcceptanceMiddleware..."
cat > apps/identity/middleware_terms.py << 'MW'
from django.shortcuts import redirect
from django.urls import reverse
from apps.identity.utils.legal import CURRENT_TERMS_VERSION

class TermsAcceptanceMiddleware:
    """Force users to accept terms before accessing the system."""
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and not request.user.is_superuser:
            allowed_paths = [
                reverse('accept-terms'),
                reverse('terms'),
                reverse('privacy'),
                reverse('logout'),
                '/static/',
                '/media/',
            ]
            
            path = request.path
            is_allowed = any(path.startswith(p) for p in allowed_paths)
            
            must_accept = (
                not getattr(request.user, 'has_accepted_terms', True)
                or getattr(request.user, 'accepted_terms_version', '') != CURRENT_TERMS_VERSION
            )
            
            if must_accept and not is_allowed:
                return redirect('accept-terms')
        
        return self.get_response(request)
MW

# =========================
# 5. REGISTER MIDDLEWARE
# =========================
echo "⚙️ Registering middleware in settings..."
if ! grep -q 'TermsAcceptanceMiddleware' config/settings/development.py; then
    sed -i '/BlockedUserMiddleware/a\    "apps.identity.middleware_terms.TermsAcceptanceMiddleware",' config/settings/development.py
fi

# =========================
# 6. ACCEPT TERMS VIEW
# =========================
echo "🧾 Creating accept_terms view..."
cat > apps/identity/views_terms.py << 'VIEW'
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
from apps.identity.utils.legal import CURRENT_TERMS_VERSION
from apps.identity.utils.network import get_client_ip

@login_required
def accept_terms_view(request):
    """Force user to accept terms before using the system."""
    if request.user.has_accepted_terms and request.user.accepted_terms_version == CURRENT_TERMS_VERSION:
        return redirect('member-dashboard')
    
    if request.method == 'POST':
        user = request.user
        user.has_accepted_terms = True
        user.accepted_terms_at = timezone.now()
        user.accepted_terms_version = CURRENT_TERMS_VERSION
        user.accepted_terms_ip = get_client_ip(request)
        user.accepted_terms_user_agent = request.META.get('HTTP_USER_AGENT', '')
        user.save()
        messages.success(request, "✅ Welcome! You have accepted the Terms of Service.")
        return redirect('member-dashboard')
    
    return render(request, 'accept_terms.html')
VIEW

# =========================
# 7. ADD URL ROUTE
# =========================
echo "🌐 Adding accept-terms URL..."
if ! grep -q 'accept-terms' config/urls.py; then
    sed -i "/from apps.identity import views_documents/a from apps.identity.views_terms import accept_terms_view" config/urls.py
    sed -i "/urlpatterns = \[/a \ \ \ \ path('accept-terms/', accept_terms_view, name='accept-terms')," config/urls.py
fi

# =========================
# 8. PATCH LOGIN VIEW — redirect to accept-terms if not accepted
# =========================
echo "🔐 Adding terms check to login view..."
python3 << 'PYEOF'
with open('apps/identity/views.py', 'r') as f:
    c = f.read()

old = "            if user.is_blocked:"
new = """            # Block login if terms not accepted
            if hasattr(user, 'has_accepted_terms') and not user.has_accepted_terms and not user.is_superuser:
                login(request, user)
                return redirect('accept-terms')
            if user.is_blocked:"""

if 'has_accepted_terms' not in c.split('if user.is_blocked:')[0]:
    c = c.replace(old, new)
    with open('apps/identity/views.py', 'w') as f:
        f.write(c)
    print('  Login view patched')
else:
    print('  Login view already patched')
PYEOF

# =========================
# 9. CREATE ACCEPT TERMS TEMPLATE
# =========================
echo "🖥️ Creating accept_terms template..."
cat > templates/accept_terms.html << 'HTML'
{% load i18n %}
<!DOCTYPE html>
<html lang="{{ LANGUAGE_CODE }}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{% trans "Accept Terms" %} — BUBABI</title>
  <style>
    * { margin:0; padding:0; box-sizing:border-box; }
    body {
      font-family:'Segoe UI', system-ui, -apple-system, sans-serif;
      min-height:100vh; display:flex; align-items:center; justify-content:center;
      background: linear-gradient(135deg, #1e293b, #0f172a);
      padding:1rem;
    }
    .card {
      background:rgba(30,41,59,0.95); backdrop-filter:blur(20px);
      padding:2.5rem 2rem; border-radius:16px;
      border:1px solid rgba(255,255,255,0.08);
      box-shadow:0 20px 60px rgba(0,0,0,0.5);
      text-align:center; max-width:500px; width:100%;
    }
    .card h2 { color:#fff; font-size:1.3rem; margin-bottom:0.5rem; }
    .card p { color:#94a3b8; font-size:0.88rem; line-height:1.6; margin-bottom:1rem; }
    .links { margin:1rem 0; }
    .links a { color:#6366f1; text-decoration:none; font-size:0.85rem; margin:0 0.5rem; display:inline-block; padding:0.3rem 0; }
    .links a:hover { text-decoration:underline; }
    .checkbox-row { display:flex; align-items:center; gap:0.5rem; justify-content:center; margin:1.5rem 0; color:#cbd5e1; font-size:0.85rem; }
    .checkbox-row input { width:18px; height:18px; accent-color:#10b981; cursor:pointer; }
    .btn { padding:0.75rem 2rem; background:#10b981; color:#fff; border:none; border-radius:10px; font-size:0.9rem; font-weight:600; cursor:pointer; width:100%; transition:background 0.15s; }
    .btn:disabled { opacity:0.4; cursor:not-allowed; }
    .btn:hover:not(:disabled) { background:#059669; }
    .logout-link { color:#ef4444; font-size:0.8rem; text-decoration:none; margin-top:1rem; display:inline-block; }
    .logout-link:hover { text-decoration:underline; }
  </style>
</head>
<body>
<div class="card">
  <div style="font-size:3rem; margin-bottom:0.5rem;">📜</div>
  <h2>{% trans "Terms & Privacy" %}</h2>
  <p>{% trans "Before continuing, you must accept our Terms of Service and Privacy Policy." %}</p>
  
  <div class="links">
    <a href="{% url 'terms' %}" target="_blank">📄 {% trans "View Terms of Service" %}</a>
    <a href="{% url 'privacy' %}" target="_blank">🔒 {% trans "View Privacy Policy" %}</a>
  </div>
  
  <form method="post">
    {% csrf_token %}
    <div class="checkbox-row">
      <input type="checkbox" id="agree" required onchange="document.getElementById('acceptBtn').disabled=!this.checked">
      <label for="agree">{% trans "I agree to the Terms of Service and Privacy Policy" %}</label>
    </div>
    <button type="submit" class="btn" id="acceptBtn" disabled>✅ {% trans "Accept & Continue" %}</button>
  </form>
  
  <a href="{% url 'logout' %}" class="logout-link">🚪 {% trans "Sign out" %}</a>
</div>
</body>
</html>
HTML

# =========================
# DONE
# =========================
echo ""
echo "✅ Terms Acceptance System Installed!"
echo "====================================="
echo " Next steps:"
echo "   1. python manage.py makemigrations identity"
echo "   2. python manage.py migrate identity"
echo "   3. Restart server"
echo ""
echo " Features:"
echo "   🔒 Login gate — terms must be accepted"
echo "   🔒 Middleware — blocks all pages until accepted"
echo "   🔒 Version tracking — forces re-accept on update"
echo "   🔒 IP + User-Agent logging"
echo "   🔒 Superuser bypass"
echo "   🔒 Clean checkbox UI"
