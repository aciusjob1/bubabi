with open('apps/identity/views.py', 'r') as f:
    content = f.read()

# Find login_view and update it
old_login = """@ensure_csrf_cookie
def login_view(request):
    if request.user.is_authenticated:
        return redirect(get_role_dashboard(request.user))
    clan = Clan.objects.first() if Clan.objects.exists() else None
    error = None
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, username=email, password=password)
        if user:
            login(request, user)
            return redirect(get_role_dashboard(user))
        error = 'Invalid email or password.'
    return render(request, 'login.html', {'error': error, 'clan': clan})"""

new_login = """@ensure_csrf_cookie
def login_view(request):
    if request.user.is_authenticated:
        return redirect(get_role_dashboard(request.user))
    clan = Clan.objects.first() if Clan.objects.exists() else None
    error = None
    email_val = ''
    
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        password = request.POST.get('password', '')
        
        user = None
        if email:
            email_val = email
            # Try email or phone via custom backend
            user = authenticate(request, email=email, password=password)
        elif phone:
            user = authenticate(request, phone=phone, password=password)
        
        if user:
            if user.is_blocked:
                error = 'Your account has been blocked. Contact a moderator.'
            else:
                login(request, user)
                
                # Log the login
                from apps.audit.services.audit_service import AuditService
                AuditService.log(
                    actor=user,
                    action='login',
                    domain='auth',
                    target=user,
                    request=request
                )
                
                next_url = request.GET.get('next', '')
                if next_url:
                    return redirect(next_url)
                return redirect(get_role_dashboard(user))
        else:
            error = 'Invalid credentials. Please try again.'
    
    return render(request, 'login.html', {
        'error': error,
        'clan': clan,
        'email': email_val
    })"""

content = content.replace(old_login, new_login)

with open('apps/identity/views.py', 'w') as f:
    f.write(content)

print("✅ Login view updated with phone support")
