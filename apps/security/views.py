
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.utils import timezone
from django.contrib.sessions.models import Session
from apps.accounts.models_session import UserSession

@staff_member_required
def kill_session(request, session_id):
    """Admin kills a user session."""
    if request.method == 'POST':
        try:
            user_session = UserSession.objects.get(id=session_id, is_active=True)
            
            # Kill Django session
            try:
                django_session = Session.objects.get(session_key=user_session.session_key)
                django_session.delete()
            except Session.DoesNotExist:
                pass
            
            # Mark as killed
            user_session.is_active = False
            user_session.logout_reason = 'admin_kill'
            user_session.expired_at = timezone.now()
            user_session.save()
            
            messages.success(request, f'Session for {user_session.user.email} terminated.')
        except UserSession.DoesNotExist:
            messages.error(request, 'Session not found.')
    
    return redirect('system')

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.utils import timezone
from django.contrib.sessions.models import Session
from apps.accounts.models_session import UserSession

@staff_member_required
def kill_session(request, session_id):
    """Admin kills a user session."""
    if request.method == 'POST':
        try:
            user_session = UserSession.objects.get(id=session_id, is_active=True)
            
            # Kill Django session
            try:
                django_session = Session.objects.get(session_key=user_session.session_key)
                django_session.delete()
            except Session.DoesNotExist:
                pass
            
            # Mark as killed
            user_session.is_active = False
            user_session.logout_reason = 'admin_kill'
            user_session.expired_at = timezone.now()
            user_session.save()
            
            messages.success(request, f'Session for {user_session.user.email} terminated.')
        except UserSession.DoesNotExist:
            messages.error(request, 'Session not found.')
    
    return redirect('system')

from django.contrib import messages
from django.utils import timezone
from apps.accounts.models_session import UserSession
from apps.core.utils.device import get_device_fingerprint, get_client_ip


@login_required
def verify_identity(request):
    """Step-up authentication when risk is detected."""
    
    # If no verification required, redirect to dashboard
    if not request.session.get('verify_required'):
        return redirect('member-dashboard')
    
    if request.method == 'POST':
        password = request.POST.get('password', '')
        
        if request.user.check_password(password):
            # Verification successful — clear flag and update session
            request.session['verify_required'] = False
            request.session.pop('risk_reasons', None)
            
            # Update session record with new device fingerprint
            session_key = request.session.session_key
            if session_key:
                UserSession.objects.filter(session_key=session_key).update(
                    device_fingerprint=get_device_fingerprint(request),
                    ip_address=get_client_ip(request),
                    risk_score=0,
                    last_activity=timezone.now()
                )
            
            messages.success(request, '✅ Identity verified. Welcome back!')
            return redirect('member-dashboard')
        else:
            messages.error(request, '❌ Incorrect password. Please try again.')
    
    return render(request, 'security/verify.html')
