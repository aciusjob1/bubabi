from django.shortcuts import redirect
from apps.identity.utils.legal import CURRENT_TERMS_VERSION

class LegalGateMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and not request.user.is_superuser:
            allowed = [
                "/accept-terms/", "/logout/", "/terms/", "/privacy/",
                "/static/", "/media/", "/admin/",
            ]
            if any(request.path.startswith(p) for p in allowed):
                return self.get_response(request)
            
            if not getattr(request.user, "has_accepted_legal", False):
                return redirect("/accept-terms/")
        
        return self.get_response(request)
