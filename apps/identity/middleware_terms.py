"""
Terms Acceptance Middleware
Enforces that users must accept terms before accessing system.
"""
import re
from django.shortcuts import redirect
from django.utils.deprecation import MiddlewareMixin

CURRENT_TERMS_VERSION = "v1"

TERMS_EXEMPT_PATTERNS = [
    re.compile(r'^/admin/login/?$'),
    re.compile(r'^/login/?$'),
    re.compile(r'^/logout/?$'),
    re.compile(r'^/accept-terms/?$'),
    re.compile(r'^/terms/?$'),
    re.compile(r'^/privacy/?$'),
    re.compile(r'^/static/.*'),
    re.compile(r'^/media/.*'),
    re.compile(r'^/health/?$'),
]


class TermsAcceptanceMiddleware(MiddlewareMixin):
    """
    Force users to accept terms before accessing the system.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.exempt_patterns = TERMS_EXEMPT_PATTERNS
        super().__init__(get_response)

    def process_request(self, request):
        """Check terms acceptance before processing request."""
        if not request.user.is_authenticated or request.user.is_superuser:
            return None
        
        path = request.path
        is_exempt = any(pattern.match(path) for pattern in self.exempt_patterns)
        
        if is_exempt:
            return None
        
        has_accepted = getattr(request.user, 'has_accepted_terms', False)
        accepted_version = getattr(request.user, 'accepted_terms_version', '')
        
        must_accept = (
            not has_accepted or 
            accepted_version != CURRENT_TERMS_VERSION
        )
        
        if must_accept:
            return redirect('accept-terms')
        
        return None
