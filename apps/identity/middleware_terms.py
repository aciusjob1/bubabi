from django.shortcuts import redirect
from apps.identity.utils.legal import CURRENT_TERMS_VERSION


class TermsAcceptanceMiddleware:
    EXEMPT_PREFIXES = (
        "/accept-terms/",
        "/login/",
        "/logout/",
        "/admin/",
        "/static/",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        # NEVER intercept exempt routes
        if any(request.path.startswith(p) for p in self.EXEMPT_PREFIXES):
            return self.get_response(request)

        # only enforce for authenticated users
        if request.user.is_authenticated:
            if not getattr(request.user, "has_accepted_terms", False):
                return redirect("accept-terms")

        return self.get_response(request)
