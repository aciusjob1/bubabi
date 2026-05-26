from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from apps.identity.models import LegalAcceptance
from apps.identity.utils.risk_engine import calculate_risk
@staff_member_required
def auditor_dashboard(request):
    records = LegalAcceptance.objects.select_related('user').order_by("-accepted_at")[:50]
    enriched = [{"record":r,"risk":calculate_risk(r.user,1)} for r in records]
    return render(request, "legal/auditor_dashboard.html", {"data": enriched})
