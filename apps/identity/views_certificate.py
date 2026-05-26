from django.shortcuts import render, get_object_or_404
from apps.identity.models import LegalAcceptance
def legal_certificate_view(request, user_id):
    record = get_object_or_404(LegalAcceptance, user_id=user_id)
    return render(request, "legal/certificate.html", {"record": record})
