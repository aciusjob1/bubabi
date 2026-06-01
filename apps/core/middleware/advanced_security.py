"""Advanced session security with risk-based authentication."""
from django.shortcuts import redirect
from django.contrib import messages
from django.utils import timezone
from apps.accounts.models_session import UserSession
from apps.core.utils.device import get_device_fingerprint, get_client_ip
from apps.security.risk_engine import calculate_risk


class AdvancedSessionSecurity:
    """Risk-based session protection."""
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            session_key = request.session.session_key
            
            if not session_key:
                request.session.save()
                session_key = request.session.session_key
            
            current_ip = get_client_ip(request)
            current_device = get_device_fingerprint(request)
            
            try:
                session = UserSession.objects.get(
                    session_key=session_key,
                    is_active=True
                )
                
                # Update tracking
                session.last_activity = timezone.now()
                session.save(update_fields=['last_activity'])
                
                # Calculate risk
                risk_score, reasons = calculate_risk(
                    session, request, current_ip, current_device
                )
                
                # Update session risk score
                session.risk_score = risk_score
                session.save(update_fields=['risk_score'])
                
                # 🚨 Critical risk: kill session
                if risk_score >= 70:
                    request.session.flush()
                    session.is_active = False
                    session.logout_reason = 'high_risk'
                    session.expired_at = timezone.now()
                    session.save()
                    messages.error(
                        request, 
                        '🚨 Session terminated: Suspicious activity detected. Please login again.'
                    )
                    return redirect('login')
                
                # ⚠️ Suspicious: require password verification
                elif risk_score >= 40:
                    # Skip verification for certain paths
                    exempt_paths = ['/login/', '/logout/', '/verify-identity/']
                    if request.path not in exempt_paths:
                        request.session['verify_required'] = True
                        request.session['risk_reasons'] = reasons
                        return redirect('verify-identity')
                    
            except UserSession.DoesNotExist:
                # Create session record if missing
                UserSession.objects.create(
                    user=request.user,
                    session_key=session_key,
                    ip_address=current_ip,
                    device_fingerprint=current_device,
                    user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
                )
        
        # Clear verification if risk is low
        if request.user.is_authenticated and request.path == '/verify-identity/':
            pass  # Don't redirect away from verification page
        
        response = self.get_response(request)
        return response
