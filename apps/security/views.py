from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
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
