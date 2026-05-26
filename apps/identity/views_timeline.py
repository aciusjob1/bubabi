from django.shortcuts import render
from apps.identity.models import LegalAcceptance
def legal_timeline(request, user_id):
    records = LegalAcceptance.objects.filter(user_id=user_id).order_by("-accepted_at")
    return render(request, "legal/timeline.html", {"records": records})
