from django.http import JsonResponse
from apps.identity.models import LegalAcceptance
def verify_legal(request, user_id):
    try:
        r = LegalAcceptance.objects.filter(user_id=user_id).latest("accepted_at")
        return JsonResponse({"status":"VALID","user":user_id,"terms":r.terms_version,"accepted_at":r.accepted_at,"certificate":r.crypto_signature or ""})
    except:
        return JsonResponse({"status":"NOT_FOUND"}, status=404)
