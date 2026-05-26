from django.shortcuts import render
from django.urls import reverse
from apps.identity.constants import MemberStatus


class BlockedUserMiddleware:
    """Middleware to show blocked page instead of flash messages."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            allowed_paths = [
                reverse('login'),
                reverse('logout'),
                reverse('register'),
                '/static/',
                '/media/',
            ]
            current_path = request.path
            is_allowed = any(current_path.startswith(p) for p in allowed_paths)

            should_block = False
            if hasattr(request.user, 'is_blocked') and request.user.is_blocked:
                should_block = True
            elif hasattr(request.user, 'status'):
                if request.user.status in [MemberStatus.SUSPENDED, MemberStatus.REMOVED, MemberStatus.INVITED]:
                    should_block = True

            if should_block and not is_allowed:
                return render(request, 'account_blocked.html', status=403)

        return self.get_response(request)
