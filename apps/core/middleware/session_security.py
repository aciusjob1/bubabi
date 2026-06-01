"""IP-based session anomaly detection."""
from django.shortcuts import redirect
from django.utils import timezone
from apps.accounts.models_session import UserSession


def get_client_ip(request):
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '0.0.0.0')


class SessionSecurityMiddleware:
    """Detect IP changes (potential session hijacking)."""
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            session_key = request.session.session_key
            current_ip = get_client_ip(request)
            
            if session_key:
                try:
                    session = UserSession.objects.get(
                        session_key=session_key,
                        is_active=True
                    )
                    
                    # Update last activity
                    session.last_activity = timezone.now()
                    session.save(update_fields=['last_activity'])
                    
                    # Check IP change (skip for localhost/127.0.0.1)
                    if session.ip_address and current_ip not in ('127.0.0.1', 'localhost'):
                        if session.ip_address != current_ip:
                            # IP changed — possible session hijack
                            request.session.flush()
                            session.is_active = False
                            session.logout_reason = 'ip_change'
                            session.expired_at = timezone.now()
                            session.save()
                            pass  # Session terminated due to IP change
                            return redirect('login')
                            
                except UserSession.DoesNotExist:
                    pass

        return self.get_response(request)
