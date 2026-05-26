from django.shortcuts import redirect
from django.urls import resolve
from .engine import must_accept_policy

EXEMPT_ROUTES = ['accept-terms', 'logout', 'terms', 'privacy']

class ComplianceMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and not request.user.is_superuser:
            current = resolve(request.path_info).url_name
            if current not in EXEMPT_ROUTES:
                if must_accept_policy(request.user, 'terms_of_service'):
                    return redirect('accept-terms')
        return self.get_response(request)
