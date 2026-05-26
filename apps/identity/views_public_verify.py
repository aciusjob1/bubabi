from django.http import JsonResponse
from apps.identity.models import LegalAcceptance
def public_verify(request, user_id):
    try:
        r = LegalAcceptance.objects.filter(user_id=user_id).latest("accepted_at")
        return JsonResponse({"status":"VERIFIED","user":user_id,"signature":r.crypto_signature or "","anchor":r.blockchain_anchor or "","accepted_at":r.accepted_at})
    except:
        return JsonResponse({"status":"NOT_FOUND"}, status=404)
