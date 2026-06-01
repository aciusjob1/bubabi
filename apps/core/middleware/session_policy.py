"""Role-based session timeout middleware."""
from django.utils.deprecation import MiddlewareMixin


class SessionPolicyMiddleware(MiddlewareMixin):
    """Apply different session timeouts based on user role."""
    
    def process_request(self, request):
        if not request.user.is_authenticated:
            return None
        
        # Superusers: 5 minutes (stricter security)
        if request.user.is_superuser:
            request.session.set_expiry(300)
        # Leaders/elders: 10 minutes
        elif hasattr(request.user, 'is_leader') and request.user.is_leader:
            request.session.set_expiry(600)
        # Regular members: 15 minutes
        else:
            request.session.set_expiry(900)
        
        return None
