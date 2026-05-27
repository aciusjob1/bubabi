from django.shortcuts import render
from apps.identity.models import Member
from apps.genealogy.models import Family

def about_view(request):
    clan = getattr(request.user, 'clan', None) if request.user.is_authenticated else None

    try:
        member_count = Member.objects.filter(clan=clan).count() if clan else Member.objects.count()
    except:
        member_count = 0

    try:
        family_count = Family.objects.count()
    except:
        family_count = 0

    modules = [
        {'icon': '🪪', 'name': 'Identity', 'desc': 'Auth, roles, lifecycle control'},
        {'icon': '💰', 'name': 'Financials', 'desc': 'Ledger, loans, fines'},
        {'icon': '🌳', 'name': 'Genealogy', 'desc': 'Family tree + lineage engine'},
        {'icon': '🏛️', 'name': 'Governance', 'desc': 'Voting + compliance'},
        {'icon': '📅', 'name': 'Events', 'desc': 'Scheduling + attendance'},
        {'icon': '📢', 'name': 'Communication', 'desc': 'Feed + SMS alerts'},
    ]

    security_items = [
        'RBAC + Least Privilege',
        'Separation of Duties',
        'Immutable Audit Logs',
        'CSRF / XSS Protection',
        'Rate Limiting',
        'Encryption in Transit',
    ]

    tech_stack = [
        'Django 6.0', 'Python 3.13', 'PostgreSQL',
        'Django REST Framework', 'Cloudinary', 'Render',
        'Chart.js', 'WhiteNoise',
    ]

    return render(request, 'about.html', {
        'member_count': member_count,
        'family_count': family_count,
        'modules': modules,
        'security_items': security_items,
        'tech_stack': tech_stack,
    })
