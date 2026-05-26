from apps.identity.models import LegalAcceptance
def export_user_legal_data(user):
    return {"user_id":str(user.id),"records":[{"terms":r.terms_version,"date":str(r.accepted_at),"ip":r.ip_address} for r in LegalAcceptance.objects.filter(user=user)]}
def delete_user_legal_data(user):
    LegalAcceptance.objects.filter(user=user).delete()
