from django.shortcuts import render, redirect
from django.contrib import messages
from apps.compliance.engine import must_accept_policy, accept_policy, get_active_policy
from apps.identity.utils.network import get_client_ip

def accept_terms_view(request):
    if not request.user.is_authenticated:
        return redirect('login')
    
    # Already accepted
    if not must_accept_policy(request.user, 'terms_of_service'):
        return redirect('member-dashboard')
    
    policy = get_active_policy('terms_of_service')
    error = None
    
    if request.method == 'POST':
        if request.POST.get('agree') != 'on':
            error = 'You must accept the Terms of Service to continue.'
        else:
            ip = get_client_ip(request)
            ua = request.META.get('HTTP_USER_AGENT', '')
            accept_policy(request.user, 'terms_of_service', ip, ua)
            messages.success(request, "Welcome! You have accepted the Terms of Service.")
            return redirect('member-dashboard')
    
    return render(request, 'accept_terms.html', {'policy': policy, 'error': error})
