from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from django.utils import timezone
from .models_session import UserSession


def get_client_ip(request):
    """Get real client IP behind proxies."""
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '0.0.0.0')


@receiver(user_logged_in)
def on_user_logged_in(sender, request, user, **kwargs):
    """Track new session on login."""
    if not request.session.session_key:
        request.session.save()
    
    # Deactivate old sessions for this user
    UserSession.objects.filter(user=user, is_active=True).update(
        is_active=False,
        logout_reason='new_login',
        expired_at=timezone.now()
    )
    
    # Create new session record
    UserSession.objects.create(
        user=user,
        session_key=request.session.session_key,
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
    )


@receiver(user_logged_out)
def on_user_logged_out(sender, request, user, **kwargs):
    """Mark session inactive on logout."""
    if request and request.session.session_key:
        UserSession.objects.filter(
            session_key=request.session.session_key
        ).update(
            is_active=False,
            logout_reason='user_logout',
            expired_at=timezone.now()
        )
