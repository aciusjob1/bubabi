from django.shortcuts import render, redirect
from django.contrib import messages
from apps.identity.utils.network import get_client_ip

def accept_terms_view(request):
    if not request.user.is_authenticated:
        return redirect('login')

    # Already accepted
    if request.user.has_accepted_terms:
        return redirect('member-dashboard')

    error = None

    if request.method == 'POST':
        if request.POST.get('agree') != 'on':
            error = 'You must accept the Terms of Service to continue.'
        else:
            request.user.has_accepted_terms = True
            request.user.save(update_fields=['has_accepted_terms'])
            messages.success(request, "Welcome! You have accepted the Terms of Service.")
            return redirect('member-dashboard')

    return render(request, 'accept_terms.html', {'error': error})
