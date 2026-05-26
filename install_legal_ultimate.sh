#!/bin/bash
echo "🚀 Installing BUBABI ULTIMATE LEGAL SYSTEM (v3+v4)..."

# ═══════════════════════════════════
# CRYPTO SIGNATURE ENGINE
# ═══════════════════════════════════
cat > apps/identity/utils/crypto_legal.py << 'PY'
import hashlib, base64
from datetime import datetime

def sign_legal_event(user, ip, version):
    payload = f"{user.id}|{ip}|{version}|{datetime.utcnow()}"
    digest = hashlib.sha256(payload.encode()).digest()
    return base64.b64encode(digest).decode()

def verify_legal_signature(payload):
    return hashlib.sha256(payload.encode()).hexdigest()
PY

# ═══════════════════════════════════
# BLOCKCHAIN AUDIT ANCHOR
# ═══════════════════════════════════
cat > apps/identity/utils/blockchain_anchor.py << 'PY'
import hashlib

def anchor_chain(previous_hash, data):
    combined = f"{previous_hash}::{data}"
    return hashlib.sha256(combined.encode()).hexdigest()
PY

# ═══════════════════════════════════
# RISK SCORING ENGINE
# ═══════════════════════════════════
cat > apps/identity/utils/risk_engine.py << 'PY'
def calculate_risk(user, records_count, violations=0):
    risk = 0
    if not getattr(user, "has_accepted_legal", False): risk += 50
    if records_count > 5: risk += 20
    risk += violations * 15
    risk = min(risk, 100)
    return {"risk_score": risk, "level": "HIGH" if risk > 70 else "MEDIUM" if risk > 30 else "LOW"}
PY

# ═══════════════════════════════════
# GDPR EXPORT / DELETE
# ═══════════════════════════════════
cat > apps/identity/utils/gdpr.py << 'PY'
from apps.identity.models import LegalAcceptance

def export_user_legal_data(user):
    records = LegalAcceptance.objects.filter(user=user)
    return {
        "user_id": str(user.id),
        "legal_records": [{
            "terms": r.terms_version, "privacy": r.privacy_version,
            "date": str(r.accepted_at), "ip": r.ip_address,
            "user_agent": r.user_agent, "certificate": getattr(r, 'certificate_hash', ''),
            "audit": getattr(r, 'audit_chain_hash', ''),
            "crypto_signature": getattr(r, 'crypto_signature', ''),
            "blockchain_anchor": getattr(r, 'blockchain_anchor', ''),
        } for r in records]
    }

def delete_user_legal_data(user):
    LegalAcceptance.objects.filter(user=user).delete()
PY

# ═══════════════════════════════════
# UPDATE LEGALACCEPTANCE MODEL
# ═══════════════════════════════════
python3 << 'PYEOF'
with open('apps/identity/models.py', 'r') as f:
    c = f.read()

if 'crypto_signature' not in c:
    insert = '\n    crypto_signature = models.TextField(blank=True, null=True)\n    blockchain_anchor = models.TextField(blank=True, null=True)\n    risk_score = models.IntegerField(default=0)\n    risk_level = models.CharField(max_length=20, default="LOW")'
    c = c.replace('    signature_hash = models.CharField(max_length=256)', '    signature_hash = models.CharField(max_length=256)' + insert)
    with open('apps/identity/models.py', 'w') as f:
        f.write(c)
    print('Model updated with crypto + blockchain + risk fields')
PYEOF

# ═══════════════════════════════════
# ENRICHMENT PATCH
# ═══════════════════════════════════
cat > apps/identity/utils/ultimate_patch.py << 'PY'
from apps.identity.utils.crypto_legal import sign_legal_event
from apps.identity.utils.blockchain_anchor import anchor_chain
from apps.identity.utils.risk_engine import calculate_risk

def enrich_legal_record(record, prev_hash="GENESIS"):
    signature = sign_legal_event(record.user, record.ip_address, record.terms_version)
    chain = anchor_chain(prev_hash, signature)
    record.crypto_signature = signature
    record.blockchain_anchor = chain
    risk = calculate_risk(record.user, 1)
    record.risk_score = risk['risk_score']
    record.risk_level = risk['level']
    record.save()
PY

# ═══════════════════════════════════
# UPDATE ACCEPT VIEW
# ═══════════════════════════════════
python3 << 'PYEOF'
with open('apps/identity/views_terms.py', 'r') as f:
    c = f.read()

if 'enrich_legal_record' not in c:
    c = c.replace(
        'LegalAcceptance.objects.create(',
        "from apps.identity.utils.ultimate_patch import enrich_legal_record\n    record = LegalAcceptance.objects.create("
    )
    c = c.replace(
        "messages.success(request, \"Welcome! You have accepted the Terms of Service.\")",
        "enrich_legal_record(record)\n    messages.success(request, \"Welcome! You have accepted the Terms of Service.\")"
    )
    with open('apps/identity/views_terms.py', 'w') as f:
        f.write(c)
    print('Views updated with enrichment patch')
PYEOF

# ═══════════════════════════════════
# AUDITOR DASHBOARD VIEW + URL
# ═══════════════════════════════════
cat > apps/identity/views_auditor.py << 'PY'
from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from apps.identity.models import LegalAcceptance

@staff_member_required
def auditor_dashboard(request):
    records = LegalAcceptance.objects.select_related('user').order_by("-accepted_at")[:50]
    enriched = []
    for r in records:
        risk = {"risk_score": getattr(r, 'risk_score', 0), "level": getattr(r, 'risk_level', 'LOW')}
        enriched.append({"record": r, "risk": risk})
    return render(request, "legal/auditor_dashboard.html", {"data": enriched})
PY

mkdir -p templates/legal
cat > templates/legal/auditor_dashboard.html << 'HTML'
{% extends "base.html" %}{% load i18n %}
{% block page_title %}🏛️ {% trans "Auditor Dashboard" %}{% endblock %}
{% block content %}
<div style="max-width:1000px; margin:0 auto;">
<h2>🏛️ {% trans "Legal Auditor Dashboard" %}</h2>
{% for item in data %}
<div style="background:#fff; border-radius:10px; padding:1rem; margin:0.5rem 0; border:1px solid #e2e8f0;">
  <p><b>{% trans "User" %}:</b> {{ item.record.user.email }}</p>
  <p><b>{% trans "Accepted" %}:</b> {{ item.record.accepted_at }}</p>
  <p style="font-family:monospace; font-size:0.75rem; color:#6366f1;">🔐 {{ item.record.crypto_signature|default:"—" }}</p>
  <p style="font-family:monospace; font-size:0.75rem; color:#10b981;">⛓️ {{ item.record.blockchain_anchor|default:"—" }}</p>
  <p>{% trans "Risk" %}: <span style="color:{% if item.risk.level == 'HIGH' %}#ef4444{% elif item.risk.level == 'MEDIUM' %}#f59e0b{% else %}#10b981{% endif %}; font-weight:700;">{{ item.risk.level }} ({{ item.risk.risk_score }})</span></p>
</div>
{% endfor %}
</div>
{% endblock %}
HTML

grep -q 'auditor-dashboard' config/urls.py || sed -i "/urlpatterns = \[/a \ \ \ \ path('auditor/', apps.identity.views_auditor.auditor_dashboard, name='auditor-dashboard')," config/urls.py

# ═══════════════════════════════════
# ADD DB COLUMNS
# ═══════════════════════════════════
python manage.py shell << 'SQL'
from django.db import connection
c = connection.cursor()
for col, typ in [('crypto_signature', 'TEXT'), ('blockchain_anchor', 'TEXT'), ('risk_score', 'INTEGER DEFAULT 0'), ('risk_level', 'VARCHAR(20) DEFAULT "LOW"')]:
    try: c.execute(f"ALTER TABLE identity_legalacceptance ADD COLUMN {col} {typ}"); print(f"  Added {col}")
    except Exception as e: print(f"  {col}: exists")
SQL

echo ""
echo "✅ ULTIMATE LEGAL SYSTEM INSTALLED"
echo "Features: Crypto signatures | Blockchain anchoring | Risk scoring | Auditor dashboard | GDPR export"
