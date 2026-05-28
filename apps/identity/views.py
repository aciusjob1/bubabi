from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.clickjacking import xframe_options_exempt
from apps.core.decorators import rate_limit
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.views.decorators.csrf import ensure_csrf_cookie
from django.http import Http404, HttpResponse
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import datetime, timedelta
import json

from apps.identity.models import Member, Person, Clan, Announcement, AnnouncementComment, Notification
from apps.identity.constants import MemberStatus
from apps.identity.services.membership_service import MembershipService
from apps.identity.notification_service import NotificationService
from apps.financials.models import Contribution, Loan, Fine, Expense
from apps.financials.constants import ContributionStatus, FineStatus, LoanStatus
from apps.financials.services.financial_service import FinancialService
from apps.audit.models import AuditLog
from apps.audit.services.audit_service import AuditService
from apps.core.sms_service import SMSService, BubabiNotifications
from apps.identity.forms import ClanSettingsForm
from apps.governance.constants import RoleLevel

svc     = FinancialService()
mem_svc = MembershipService()


# ══════════════════════════════════════════════
# PERMISSION HELPERS
# ══════════════════════════════════════════════

def is_superuser(user):
    return user.is_authenticated and user.is_superuser

def is_leader(user):
    if not user.is_authenticated: return False
    if user.is_superuser: return True
    return user.clan_roles.filter(is_active=True, role__hierarchy_level__gte=RoleLevel.LEADER).exists()

def is_treasurer(user):
    if not user.is_authenticated: return False
    if user.is_superuser: return True
    return user.clan_roles.filter(is_active=True, role__hierarchy_level__gte=RoleLevel.TREASURER).exists()

def is_secretary(user):
    if not user.is_authenticated: return False
    if user.is_superuser: return True
    return user.clan_roles.filter(is_active=True, role__hierarchy_level__gte=RoleLevel.SECRETARY).exists()

def is_moderator(user):
    if not user.is_authenticated: return False
    if user.is_superuser: return True
    return user.clan_roles.filter(is_active=True, role__hierarchy_level__gte=4).exists()

def is_elder_or_above(user):
    if not user.is_authenticated: return False
    if user.is_superuser: return True
    return user.clan_roles.filter(is_active=True, role__hierarchy_level__gte=RoleLevel.ELDER).exists()

superuser_required  = user_passes_test(is_superuser, login_url='member-dashboard')
leader_required     = user_passes_test(is_leader, login_url='member-dashboard')
treasurer_required  = user_passes_test(is_treasurer, login_url='member-dashboard')
secretary_required  = user_passes_test(is_secretary, login_url='member-dashboard')
moderator_required  = user_passes_test(is_moderator, login_url='member-dashboard')
elder_required      = user_passes_test(is_elder_or_above, login_url='member-dashboard')


# ══════════════════════════════════════════════
# AUTH
# ══════════════════════════════════════════════

@ensure_csrf_cookie
@rate_limit("login", 20, 300)
def login_view(request):
    if request.user.is_authenticated:
        return redirect(get_role_dashboard(request.user))
    clan = Clan.objects.first() if Clan.objects.exists() else None
    clan_banner = clan.banner_image if clan and clan.banner_image else None
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
            # Block login if terms not accepted
            if hasattr(user, "has_accepted_terms") and not user.has_accepted_terms and not user.is_superuser:
                login(request, user)
                return redirect("accept-terms")
            if user.is_blocked:
                return render(request, "account_blocked.html", {"reason": user.block_reason}, status=403)
            elif user.status == 'pending':
                login(request, user)
                return redirect('registration-pending')
            elif user.status == 'suspended':
                error = 'Your account has been suspended. Contact clan leadership.'
            elif user.status == 'removed':
                error = 'Your account has been removed from the clan.'
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
        'email': email_val,
        'clan_banner': clan.banner_image if clan and clan.banner_image else None
    })


def logout_view(request):
    logout(request)
    return redirect('login')


def get_role_dashboard(user):
    if user.is_superuser:
        return 'system'
    roles = user.clan_roles.filter(is_active=True).select_related('role')
    if not roles.exists():
        return 'member-dashboard'
    highest = max(roles, key=lambda r: r.role.hierarchy_level)
    level = highest.role.hierarchy_level
    if level >= RoleLevel.LEADER:    return 'dashboard'
    elif level >= 4:                 return 'moderator'
    elif level >= RoleLevel.TREASURER: return 'treasurer'
    elif level >= RoleLevel.SECRETARY: return 'secretary'
    elif level >= RoleLevel.ELDER:   return 'elder'
    return 'member-dashboard'


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    from apps.genealogy.models import Family
    clans = Clan.objects.filter(is_public=True)
    families = Family.objects.all()
    clan = clans.first() if clans.exists() else None
    
    # If no public clans, show closed page instead of empty form
    if not clans.exists():
        # Use first clan for branding (logo, banner, colors) even if not public
        branding_clan = Clan.objects.first()
        return render(request, 'registration/closed.html', {
            'clan': branding_clan,
        })
    
    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        phone = request.POST.get('phone', '').strip()
        gender = request.POST.get('gender', '')
        birth_date = request.POST.get('birth_date', '')
        clan_id = request.POST.get('clan_id', '')
        family_id = request.POST.get('family_id', '')
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')
        errors = {}
        if not full_name: errors['full_name'] = ['Full name is required.']
        if not email: errors['email'] = ['Email is required.']
        elif Member.objects.filter(email=email).exists(): errors['email'] = ['A member with this email already exists.']
        if not clan_id: errors['clan_id'] = ['Please select your clan.']
        if not password1: errors['password1'] = ['Password is required.']
        elif len(password1) < 6: errors['password1'] = ['Password must be at least 6 characters.']
        if password1 != password2: errors['password2'] = ['Passwords do not match.']
        if errors:
            return render(request, 'registration/register.html', {
                'form': {'errors': errors, 'full_name': {'value': full_name}, 'email': {'value': email}, 'phone': {'value': phone}, 'gender': {'value': gender}, 'birth_date': {'value': birth_date}, 'clan_id': {'value': clan_id}, 'family_id': {'value': family_id}},
                'clan': clan, 'clans': clans, 'families': families,
                'clan_banner': clan.banner_image if clan and clan.banner_image else None,
            })
        try:
            selected_clan = Clan.objects.get(id=clan_id, is_public=True)
        except Clan.DoesNotExist:
            errors['clan_id'] = ['Invalid clan or clan not accepting public registrations.']
            return render(request, 'registration/register.html', {
                'form': {'errors': errors, 'full_name': {'value': full_name}, 'email': {'value': email}, 'phone': {'value': phone}, 'gender': {'value': gender}, 'birth_date': {'value': birth_date}, 'clan_id': {'value': clan_id}, 'family_id': {'value': family_id}},
                'clan': clan, 'clans': clans, 'families': families,
                'clan_banner': clan.banner_image if clan and clan.banner_image else None,
            })
        person = Person.objects.create(full_name=full_name, gender=gender or 'other', birth_date=birth_date or '2000-01-01')
        member = Member.objects.create_user(email=email, password=password1, person=person, phone=phone, clan=selected_clan, status=MemberStatus.PENDING)
        
        # Auto-assign default Member role
        from apps.governance.models import Role, MemberRole
        default_role, _ = Role.objects.get_or_create(
            name='Member', clan=selected_clan,
            defaults={'hierarchy_level': 0, 'description': 'Default clan member role', 'clan': selected_clan}
        )
        MemberRole.objects.update_or_create(
            member=member, role=default_role,
            defaults={'is_active': True, 'assigned_by': member}
        )
        if family_id:
            try:
                from apps.genealogy.models import PersonFamilyMembership
                family = Family.objects.get(id=family_id)
                PersonFamilyMembership.objects.create(person=person, family=family)
            except: pass
        # Don't auto-login — show pending approval page instead
        messages.success(request, f"Registration submitted! Your account is pending approval by clan leadership.")
        
        # Notify superusers and clan leaders about new pending member
        try:
            from apps.identity.models import Notification
            # Notify superusers
            superusers = Member.objects.filter(is_superuser=True, status='active')
            for admin in superusers:
                Notification.objects.create(
                    recipient=admin,
                    notif_type='member_invited',
                    title='New Member Pending Approval',
                    message=f'{person.full_name} ({email}) has registered and is pending approval for {selected_clan.name} clan.',
                    link=f'/admin/identity/member/{member.id}/change/'
                )
            # Notify clan leaders/elders
            leaders = Member.objects.filter(clan=selected_clan, status='active').filter(
                Q(is_elder=True) | Q(is_superuser=True)
            ).distinct()
            for leader in leaders:
                if leader not in superusers:  # Avoid duplicate notifications
                    Notification.objects.create(
                        recipient=leader,
                        notif_type='member_invited',
                        title='New Member Pending Approval',
                        message=f'{person.full_name} ({email}) has registered and is pending approval for your clan {selected_clan.name}.',
                        link=f'/members/'
                    )
        except Exception as e:
            pass  # Fail silently - don't block registration
        
        return redirect('registration-pending')
    return render(request, 'registration/register.html', {
        'form': {'errors': {}, 'full_name': {'value': ''}, 'email': {'value': ''}, 'phone': {'value': ''}, 'gender': {'value': ''}, 'birth_date': {'value': ''}, 'clan_id': {'value': ''}, 'family_id': {'value': ''}},
        'clan': clan, 'clans': clans, 'families': families,
        'clan_banner': clan.banner_image if clan and clan.banner_image else None,
    })


# ══════════════════════════════════════════════
# DASHBOARDS
# ══════════════════════════════════════════════


@leader_required
def dashboard(request):
    clan = request.user.clan
    from apps.genealogy.models import Family
    context = {
        'clan': clan, 'balance': svc.get_clan_balance(clan),
        'active_count': Member.objects.filter(clan=clan, status=MemberStatus.ACTIVE).count(),
        'total_members': Member.objects.filter(clan=clan).count(),
        'family_count': Family.objects.filter(clan=clan).count(),
        'due_count': Contribution.objects.filter(member__clan=clan, status=ContributionStatus.DUE).count(),
        'late_count': Contribution.objects.filter(member__clan=clan, status=ContributionStatus.LATE).count(),
        'unpaid_fines': Fine.objects.filter(member__clan=clan, status=FineStatus.UNPAID).count(),
        'recent_contributions': Contribution.objects.filter(member__clan=clan).select_related('member__person').order_by('-due_date')[:10],
        'recent_audit': AuditLog.objects.select_related('actor__person').order_by('-timestamp')[:8],
    }
    return render(request, 'dashboard.html', context)



@treasurer_required
def treasurer_dashboard(request):
    clan = request.user.clan
    today = timezone.now().date()
    late_contributions = list(Contribution.objects.filter(member__clan=clan, status=ContributionStatus.LATE).select_related('member__person'))
    for c in late_contributions: c.days_late = (today - c.due_date).days
    # Counts for stat cards
    paid_count = Contribution.objects.filter(member__clan=clan, status=ContributionStatus.PAID).count()
    due_count = Contribution.objects.filter(member__clan=clan, status=ContributionStatus.DUE).count()
    late_count = Contribution.objects.filter(member__clan=clan, status=ContributionStatus.LATE).count()
    unpaid_fines = Fine.objects.filter(member__clan=clan, status=FineStatus.UNPAID).count()
    loans_outstanding = Loan.objects.filter(borrower__clan=clan, status__in=['approved', 'disbursed']).aggregate(Sum('amount_approved'))['amount_approved__sum'] or 0
    unverified = Contribution.objects.filter(member__clan=clan, status=ContributionStatus.PAID, verified_by__isnull=True).select_related('member__person', 'recorded_by__person')
    
    context = {
        'balance': svc.get_clan_balance(clan),
        'total_collected': Contribution.objects.filter(member__clan=clan, status=ContributionStatus.PAID).aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0,
        'total_expenses': Expense.objects.filter(clan=clan).aggregate(Sum('amount'))['amount__sum'] or 0,
        'late_contributions': late_contributions[:10],
        'unpaid_fines_list': Fine.objects.filter(member__clan=clan, status=FineStatus.UNPAID).select_related('member__person')[:10],
        'paid_count': paid_count,
        'due_count': due_count,
        'late_count': late_count,
        'unpaid_fines': unpaid_fines,
        'loans_outstanding': loans_outstanding,
        'unverified': unverified,
    }
    return render(request, 'treasurer.html', context)



@secretary_required
def secretary_dashboard(request):
    from apps.events.models import ClanEvent
    clan = request.user.clan
    now = timezone.now()
    context = {
        'active_count': Member.objects.filter(clan=clan, status=MemberStatus.ACTIVE).count(),
        'pending_count': Member.objects.filter(clan=clan, status=MemberStatus.PENDING).count(),
        'pending_members': Member.objects.filter(clan=clan, status__in=[MemberStatus.INVITED, MemberStatus.PENDING]).select_related('person', 'invited_by__person')[:10],
        'upcoming_events': ClanEvent.objects.filter(clan=clan, is_cancelled=False, scheduled_at__gte=now).order_by('scheduled_at')[:10],
    }
    return render(request, 'secretary.html', context)



@elder_required
def elder_dashboard(request):
    from apps.genealogy.models import Family
    from apps.governance.models import Vote
    from apps.governance.constants import VoteStatus
    clan = request.user.clan
    elders = [m for m in Member.objects.filter(clan=clan, status=MemberStatus.ACTIVE).select_related('person').prefetch_related('clan_roles__role') if m.is_elder]
    context = {
        'clan': clan,
        'family_count': Family.objects.filter(clan=clan).count(),
        'persons_count': Person.objects.count(),
        'elder_count': len(elders),
        'deceased_count': Person.objects.filter(death_date__isnull=False).count(),
        'families': Family.objects.filter(clan=clan).select_related('founding_person')[:20],
        'open_votes': Vote.objects.filter(clan=clan, status=VoteStatus.OPEN).select_related('initiated_by__person'),
        'elders': elders,
    }
    return render(request, 'elder.html', context)



@login_required
def member_dashboard(request):
    # Block pending/suspended/removed users
    if hasattr(request.user, 'status'):
        if request.user.status == 'pending':
            return redirect('registration-pending')
        elif request.user.status == 'suspended':
            return render(request, "account_blocked.html", {"reason": "Your account has been suspended."}, status=403)
        elif request.user.status == 'removed':
            return render(request, "account_blocked.html", {"reason": "Your account has been removed."}, status=403)
    member = request.user
    my_contributions = Contribution.objects.filter(member=member).order_by('-due_date')
    my_balance_due = my_contributions.filter(status__in=[ContributionStatus.DUE, ContributionStatus.LATE, ContributionStatus.PENALIZED]).aggregate(total=Sum('amount_due'))['total'] or 0
    context = {
        'my_contributions': my_contributions[:10],
        'my_balance_due': my_balance_due,
        'my_unpaid_fines': Fine.objects.filter(member=member, status=FineStatus.UNPAID).count(),
        'my_loans': Loan.objects.filter(borrower=member).order_by('-created_at')[:5],
    }
    return render(request, 'member_dashboard.html', context)



@superuser_required
def system_dashboard(request):
    from apps.financials.models import LedgerEntry
    from apps.genealogy.models import Relationship
    from apps.governance.models import VoteCast
    all_clans = [{'clan': c, 'member_count': Member.objects.filter(clan=c).count(), 'balance': svc.get_clan_balance(c)} for c in Clan.objects.all()]
    context = {
        'total_clans': Clan.objects.count(), 'total_members': Member.objects.count(),
        'total_persons': Person.objects.count(), 'audit_count': AuditLog.objects.count(),
        'contribution_count': Contribution.objects.count(), 'ledger_count': LedgerEntry.objects.count(),
        'relationship_count': Relationship.objects.count(), 'votes_count': VoteCast.objects.count(),
        'all_clans': all_clans,
        'pending_members': Member.objects.filter(status='pending').select_related('person', 'clan').order_by('-created_at'),
        'all_members': Member.objects.select_related('person', 'clan').order_by('clan__name', 'person__full_name'),
        'recent_audit': AuditLog.objects.select_related('actor').order_by('-timestamp')[:20],
    }
    return render(request, 'system.html', context)


# ══════════════════════════════════════════════
# GENERAL PAGES
# ══════════════════════════════════════════════


@login_required
def members_view(request):
    clan = request.user.clan
    search = request.GET.get('search', '').strip()
    members = Member.objects.filter(clan=clan).select_related('person')
    if search:
        members = members.filter(Q(person__full_name__icontains=search) | Q(email__icontains=search) | Q(phone__icontains=search))
    members = members.order_by('person__full_name')
    context = {
        'members': members,
        'active_count': members.filter(status=MemberStatus.ACTIVE).count(),
        'pending_count': members.filter(status=MemberStatus.PENDING).count(),
        'suspended_count': members.filter(status=MemberStatus.SUSPENDED).count(),
        'elder_count': sum(1 for m in members if m.is_elder),
    }
    return render(request, 'members.html', context)



@login_required
def member_profile(request, pk):
    member = get_object_or_404(Member, pk=pk, clan=request.user.clan)
    from apps.genealogy.models import PersonFamilyMembership
    from apps.governance.models import MemberRole
    context = {
        'profile_member': member,
        'contributions': Contribution.objects.filter(member=member).order_by('-due_date')[:10],
        'loans': Loan.objects.filter(borrower=member).order_by('-created_at')[:5],
        'fines': Fine.objects.filter(member=member).order_by('-created_at')[:5],
        'status_history': member.status_history.all()[:10],
        'roles': MemberRole.objects.filter(member=member, is_active=True).select_related('role'),
        'families': PersonFamilyMembership.objects.filter(person=member.person).select_related('family') if member.person else [],
    }
    return render(request, 'profile.html', context)



def contributions_view(request):
    clan = request.user.clan
    contributions = Contribution.objects.filter(member__clan=clan).select_related('member__person', 'verified_by__person')
    user = request.user
    is_treasurer = user.clan_roles.filter(is_active=True, role__hierarchy_level__gte=RoleLevel.TREASURER).exists()
    is_leader = user.clan_roles.filter(is_active=True, role__hierarchy_level__gte=RoleLevel.LEADER).exists()
    if not (is_treasurer or is_leader or user.is_superuser):
        contributions = contributions.filter(member=user)
    search = request.GET.get('search', '').strip()
    if search:
        contributions = contributions.filter(Q(member__person__full_name__icontains=search) | Q(member__email__icontains=search) | Q(period_label__icontains=search))
    status_filter = request.GET.get('status', 'all')
    if status_filter != 'all':
        contributions = contributions.filter(status=status_filter)
    contributions = contributions.order_by('-due_date', 'member__person__full_name')
    total_due = contributions.aggregate(Sum('amount_due'))['amount_due__sum'] or 0
    total_paid = contributions.aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0
    total_balance = total_due - total_paid
    collection_rate = round((total_paid / total_due * 100) if total_due > 0 else 0, 1)
    return render(request, 'contributions.html', {
        'contributions': contributions, 'total_due': total_due, 'total_paid': total_paid,
        'total_balance': total_balance, 'collection_rate': collection_rate,
        'current_filter': status_filter, 'today': timezone.now().date(),
        'is_treasurer': is_treasurer or is_leader or user.is_superuser,
    })



def loans_view(request):
    clan = request.user.clan
    user = request.user
    is_treasurer = user.clan_roles.filter(is_active=True, role__hierarchy_level__gte=RoleLevel.TREASURER).exists() or user.is_superuser
    loans = Loan.objects.filter(borrower__clan=clan)
    if not is_treasurer:
        loans = loans.filter(borrower=user)
    loans = loans.select_related('borrower__person').order_by('-created_at')
    return render(request, 'loans.html', {'loans': loans, 'is_treasurer': is_treasurer})



def fines_view(request):
    fines = Fine.objects.filter(member__clan=request.user.clan).select_related('member__person', 'issued_by__person').order_by('-created_at')
    return render(request, 'fines.html', {'fines': fines})



@elder_required
def audit_view(request):
    logs = AuditLog.objects.select_related('actor__person').order_by('-timestamp')[:100]
    return render(request, 'audit.html', {'logs': logs})



def reports_view(request):
    clan = request.user.clan
    monthly_data = []
    periods = Contribution.objects.filter(member__clan=clan).values('period_label').distinct().order_by('period_label')
    for p in periods:
        label = p['period_label']
        paid = Contribution.objects.filter(member__clan=clan, period_label=label, status=ContributionStatus.PAID).aggregate(Sum('amount_paid'))['amount_paid__sum'] or 0
        expected = Contribution.objects.filter(member__clan=clan, period_label=label).aggregate(Sum('amount_due'))['amount_due__sum'] or 0
        monthly_data.append({'period': label, 'paid': paid, 'expected': expected, 'rate': round((paid / expected * 100) if expected else 0, 1)})
    expense_by_category = Expense.objects.filter(clan=clan).values('category').annotate(total=Sum('amount'), count=Count('id')).order_by('-total')
    return render(request, 'reports.html', {
        'monthly_data': monthly_data, 'expense_by_category': expense_by_category,
        'total_collected': sum(m['paid'] for m in monthly_data),
        'collection_rate': round(sum(m['paid'] for m in monthly_data) / sum(m['expected'] for m in monthly_data) * 100 if monthly_data and sum(m['expected'] for m in monthly_data) > 0 else 0, 1),
        'balance': svc.get_clan_balance(clan),
    })


# ══════════════════════════════════════════════
# IDENTITY ACTIONS
# ══════════════════════════════════════════════


@secretary_required
def add_person(request):
    from apps.identity.forms import PersonForm
    if request.method == 'POST':
        form = PersonForm(request.POST)
        if form.is_valid():
            person = form.save()
            AuditService.log(actor=request.user, action='person.created', domain='genealogy', target=person, request=request)
            messages.success(request, f"'{person.full_name}' added.")
            return redirect('members')
    else:
        form = PersonForm()
    return render(request, 'forms/person_form.html', {'form': form})



@secretary_required
def invite_member_view(request):
    from apps.identity.forms import InviteMemberForm
    if request.method == 'POST':
        form = InviteMemberForm(request.POST)
        if form.is_valid():
            try:
                person = Person.objects.create(full_name=form.cleaned_data['full_name'], gender=form.cleaned_data['gender'], birth_date=form.cleaned_data['birth_date'])
                mem_svc.invite_member(person=person, clan=request.user.clan, email=form.cleaned_data['email'], phone=form.cleaned_data.get('phone', ''), invited_by=request.user, request=request)
                messages.success(request, f"{person.full_name} invited successfully.")
                return redirect('members')
            except Exception as e: messages.error(request, str(e))
    else:
        form = InviteMemberForm()
    return render(request, 'forms/invite_form.html', {'form': form})



@leader_required
def change_member_status(request, pk):
    member = get_object_or_404(Member, pk=pk, clan=request.user.clan)
    from apps.identity.forms import TransitionMemberForm
    if request.method == 'POST':
        form = TransitionMemberForm(request.POST)
        if form.is_valid():
            try:
                mem_svc.transition_status(member=member, new_status=form.cleaned_data['new_status'], changed_by=request.user, reason=form.cleaned_data.get('reason', ''), request=request)
                messages.success(request, f"Status updated to {form.cleaned_data['new_status']}.")
                return redirect('members')
            except Exception as e: messages.error(request, str(e))
    else:
        form = TransitionMemberForm()
    return render(request, 'forms/status_form.html', {'form': form, 'member': member})


# ══════════════════════════════════════════════
# ROLE ASSIGNMENT
# ══════════════════════════════════════════════


def assign_leader_view(request, pk):
    # Protected action: requires elder approval if not superuser
    if not request.user.is_superuser and action == "assign":
        from apps.governance.models import ApprovalRequest
        existing = ApprovalRequest.objects.filter(action_type="assign_leader", payload__member_id=str(pk), status="pending").exists()
        if not existing:
            messages.info(request, "Assigning a Leader requires Elder Council approval. An approval request has been created.")
            ApprovalRequest.objects.create(
                clan=request.user.clan,
                action_type="assign_leader",
                description=f"Assign {member.person.full_name} as Leader",
                payload={"member_id": str(pk), "action": "assign"},
                initiated_by=request.user,
                minimum_approvals=3
            )
            return redirect("members")
    if not request.user.is_superuser:
        messages.error(request, "Only the Super Admin can assign/remove Leaders.")
        return redirect('members')
    member = get_object_or_404(Member, pk=pk, clan=request.user.clan)
    from apps.governance.models import Role, MemberRole
    leader_role, _ = Role.objects.get_or_create(name='Leader', clan=member.clan, defaults={'hierarchy_level': 5, 'description': 'Clan Leader'})
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'assign':
            MemberRole.objects.update_or_create(
                member=member, role=leader_role,
                defaults={'is_active': True, 'assigned_by': request.user}
            )
            messages.success(request, f"{member.person.full_name} is now a Leader.")
        elif action == 'remove':
            MemberRole.objects.filter(member=member, role=leader_role).update(is_active=False)
            messages.success(request, f"Leader role removed from {member.person.full_name}.")
        return redirect('member-profile', pk=member.id)
    is_leader = MemberRole.objects.filter(member=member, role=leader_role, is_active=True).exists()
    return render(request, 'forms/assign_role.html', {'member': member, 'role_name': 'Leader', 'has_role': is_leader})



def assign_elder_view(request, pk):
    member = get_object_or_404(Member, pk=pk, clan=request.user.clan)
    is_leader = request.user.clan_roles.filter(is_active=True, role__hierarchy_level__gte=5).exists()
    if not request.user.is_superuser and not is_leader:
        messages.error(request, "Only the Super Admin or Clan Leader can assign/remove Elders.")
        return redirect('members')
    from apps.governance.models import Role, MemberRole
    elder_role, _ = Role.objects.get_or_create(name='Elder', clan=member.clan, defaults={'hierarchy_level': 1, 'description': 'Clan Elder'})
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'assign':
            MemberRole.objects.update_or_create(
                member=member, role=elder_role,
                defaults={'is_active': True, 'assigned_by': request.user}
            )
            messages.success(request, f"{member.person.full_name} is now an Elder.")
        elif action == 'remove':
            MemberRole.objects.filter(member=member, role=elder_role).update(is_active=False)
            messages.success(request, f"Elder role removed from {member.person.full_name}.")
        return redirect('member-profile', pk=member.id)
    is_elder = MemberRole.objects.filter(member=member, role=elder_role, is_active=True).exists()
    return render(request, 'forms/assign_role.html', {'member': member, 'role_name': 'Elder', 'has_role': is_elder})



def assign_moderator_view(request, pk):
    member = get_object_or_404(Member, pk=pk, clan=request.user.clan)
    is_leader = request.user.clan_roles.filter(is_active=True, role__hierarchy_level__gte=5).exists()
    if not request.user.is_superuser and not is_leader:
        messages.error(request, "Only the Super Admin or Clan Leader can manage moderators.")
        return redirect('members')
    from apps.governance.models import Role, MemberRole
    mod_role, _ = Role.objects.get_or_create(name='Moderator', clan=member.clan, defaults={'hierarchy_level': 4, 'description': 'Clan Moderator'})
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'assign':
            MemberRole.objects.update_or_create(
                member=member, role=mod_role,
                defaults={'is_active': True, 'assigned_by': request.user}
            )
            messages.success(request, f"{member.person.full_name} is now a Moderator.")
        elif action == 'remove':
            MemberRole.objects.filter(member=member, role=mod_role).update(is_active=False)
            messages.success(request, f"Moderator role removed from {member.person.full_name}.")
        return redirect('member-profile', pk=member.id)
    is_mod = MemberRole.objects.filter(member=member, role=mod_role, is_active=True).exists()
    return render(request, 'forms/assign_role.html', {'member': member, 'role_name': 'Moderator', 'has_role': is_mod})


# ══════════════════════════════════════════════
# BLOCK / UNBLOCK
# ══════════════════════════════════════════════


def assign_treasurer_view(request, pk):
    member = get_object_or_404(Member, pk=pk, clan=request.user.clan)
    is_leader = request.user.clan_roles.filter(is_active=True, role__hierarchy_level__gte=5).exists()
    if not request.user.is_superuser and not is_leader:
        messages.error(request, "Only the Super Admin or Clan Leader can manage roles.")
        return redirect('members')
    from apps.governance.models import Role, MemberRole
    role, _ = Role.objects.get_or_create(name="Treasurer", clan=member.clan, defaults={"hierarchy_level": 3, "description": "Clan Treasurer"})
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'assign':
            MemberRole.objects.update_or_create(member=member, role=role, defaults={"is_active": True, "assigned_by": request.user})
            messages.success(request, f"{member.person.full_name} is now a Treasurer.")
        elif action == 'remove':
            MemberRole.objects.filter(member=member, role=role).update(is_active=False)
            messages.success(request, f"Treasurer role removed from {member.person.full_name}.")
        return redirect('member-profile', pk=member.id)
    return render(request, 'forms/assign_role.html', {"member": member, "role_name": "Treasurer", "has_role": MemberRole.objects.filter(member=member, role=role, is_active=True).exists()})


def assign_secretary_view(request, pk):
    member = get_object_or_404(Member, pk=pk, clan=request.user.clan)
    is_leader = request.user.clan_roles.filter(is_active=True, role__hierarchy_level__gte=5).exists()
    if not request.user.is_superuser and not is_leader:
        messages.error(request, "Only the Super Admin or Clan Leader can manage roles.")
        return redirect('members')
    from apps.governance.models import Role, MemberRole
    role, _ = Role.objects.get_or_create(name="Secretary", clan=member.clan, defaults={"hierarchy_level": 2, "description": "Clan Secretary"})
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'assign':
            MemberRole.objects.update_or_create(member=member, role=role, defaults={"is_active": True, "assigned_by": request.user})
            messages.success(request, f"{member.person.full_name} is now a Secretary.")
        elif action == 'remove':
            MemberRole.objects.filter(member=member, role=role).update(is_active=False)
            messages.success(request, f"Secretary role removed from {member.person.full_name}.")
        return redirect('member-profile', pk=member.id)
    return render(request, 'forms/assign_role.html', {"member": member, "role_name": "Secretary", "has_role": MemberRole.objects.filter(member=member, role=role, is_active=True).exists()})




@leader_required
def blocked_members_view(request):
    """List all blocked members for the clan."""
    clan = request.user.clan
    blocked = Member.objects.filter(clan=clan, is_blocked=True).select_related("person", "blocked_by__person").order_by("-blocked_at")
    return render(request, "blocked_members.html", {"blocked_members": blocked})

@moderator_required
def block_member_view(request, pk):
    member = get_object_or_404(Member, pk=pk, clan=request.user.clan)
    is_moderator = request.user.clan_roles.filter(is_active=True, role__hierarchy_level__gte=4).exists()
    if not request.user.is_superuser and not is_moderator:
        messages.error(request, "Only Super Admin, Leader, or Moderator can block members.")
        return redirect('members')
    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        member.is_blocked = True
        member.blocked_at = timezone.now()
        member.blocked_by = request.user
        member.block_reason = reason
        member.save()
        messages.success(request, f"{member.person.full_name} has been blocked.")
        return redirect('member-profile', pk=member.id)
    return render(request, 'forms/block_member.html', {'member': member})



@moderator_required
def unblock_member_view(request, pk):
    member = get_object_or_404(Member, pk=pk, clan=request.user.clan)
    is_moderator = request.user.clan_roles.filter(is_active=True, role__hierarchy_level__gte=4).exists()
    if not request.user.is_superuser and not is_moderator:
        messages.error(request, "Only Super Admin, Leader, or Moderator can unblock members.")
        return redirect('members')
    if request.method == 'POST':
        member.is_blocked = False
        member.blocked_at = None
        member.blocked_by = None
        member.block_reason = ''
        member.save()
        messages.success(request, f"{member.person.full_name} has been unblocked.")
        return redirect('member-profile', pk=member.id)
    return redirect('member-profile', pk=member.id)


# ══════════════════════════════════════════════
# CLAN SETTINGS
# ══════════════════════════════════════════════


@superuser_required
def clan_settings_view(request):
    clan = request.user.clan
    if request.method == 'POST':
        form = ClanSettingsForm(request.POST, request.FILES, instance=clan)
        if form.is_valid():
            form.save()
            messages.success(request, "Clan settings updated successfully!")
            return redirect('clan-settings')
    else:
        form = ClanSettingsForm(instance=clan)
    return render(request, 'clan_settings.html', {'form': form, 'clan': clan})


# ══════════════════════════════════════════════
# NOTIFICATIONS
# ══════════════════════════════════════════════


def notifications_view(request):
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    notifications = Notification.objects.filter(recipient=request.user).order_by('-sent_at')[:50]
    return render(request, 'notifications.html', {'notifications': notifications})



def mark_notification_read(request, pk):
    try:
        notif = Notification.objects.get(pk=pk, recipient=request.user)
        notif.is_read = True
        notif.save()
        if notif.link: return redirect(notif.link)
    except Notification.DoesNotExist: pass
    return redirect('notifications')



def mark_all_notifications_read(request):
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    messages.success(request, "All notifications marked as read.")
    return redirect('notifications')


# ══════════════════════════════════════════════
# ANNOUNCEMENTS
# ══════════════════════════════════════════════


def announcements_view(request):
    clan = request.user.clan
    now = timezone.now()
    if clan:
        Announcement.objects.filter(clan=clan, is_active=True, expires_at__isnull=False, expires_at__lt=now).update(is_active=False)
        announcements = Announcement.objects.filter(clan=clan, is_active=True).exclude(hidden_by=request.user).select_related('author__person').prefetch_related('comments').order_by('-is_pinned', '-created_at')
    else:
        announcements = Announcement.objects.none()
    return render(request, 'announcements.html', {'announcements': announcements, 'now': now})



@secretary_required
def create_announcement(request):
    from apps.identity.forms import AnnouncementForm
    if not request.user.clan:
        messages.error(request, "You must be assigned to a clan first.")
        return redirect('announcements')
    if request.method == 'POST':
        form = AnnouncementForm(request.POST)
        if form.is_valid():
            announcement = form.save(commit=False)
            announcement.clan = request.user.clan
            announcement.author = request.user
            duration = request.POST.get('duration_days')
            if duration: announcement.expires_at = timezone.now() + timedelta(days=int(duration))
            announcement.is_pinned = request.POST.get('is_pinned') == 'on'
            announcement.save()
            NotificationService.notify_announcement(announcement)
            if request.POST.get('send_sms') == 'on':
                try:
                    active_members = Member.objects.filter(clan=request.user.clan, status=MemberStatus.ACTIVE)
                    if active_members.exists(): BubabiNotifications.announcement_broadcast(announcement, active_members)
                except Exception as e: print(f"SMS broadcast error: {e}")
            AuditService.log(actor=request.user, action='announcement.created', domain='membership', target=announcement, request=request)
            messages.success(request, "Announcement posted successfully!")
            return redirect('announcements')
    else:
        form = AnnouncementForm()
    return render(request, 'forms/announcement_form.html', {'form': form})



def announcement_detail(request, pk):
    announcement = get_object_or_404(Announcement, pk=pk, clan=request.user.clan)
    if not announcement.is_active and request.user != announcement.author and not request.user.is_superuser:
        raise Http404("Announcement not found.")
    comments = announcement.comments.select_related('author__person').order_by('created_at')
    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        if content:
            if len(content) > 500: messages.error(request, "Comment must be under 500 characters.")
            else:
                AnnouncementComment.objects.create(announcement=announcement, author=request.user, content=content)
                messages.success(request, "Comment added.")
            return redirect('announcement-detail', pk=announcement.pk)
    return render(request, 'announcement_detail.html', {'announcement': announcement, 'comments': comments})



def delete_announcement(request, pk):
    announcement = get_object_or_404(Announcement, pk=pk, clan=request.user.clan, is_active=True)
    if request.user == announcement.author or request.user.is_superuser:
        announcement.is_active = False
        announcement.save()
        AuditService.log(actor=request.user, action='announcement.deleted', domain='membership', target=announcement, request=request)
        messages.success(request, "Announcement deleted for everyone.")
    else:
        announcement.hidden_by.add(request.user)
        messages.success(request, "Announcement hidden from your view.")
    return redirect('announcements')


# ══════════════════════════════════════════════
# FAMILY TREE
# ══════════════════════════════════════════════


def family_tree_view(request, person_pk=None):
    from apps.genealogy.services.genealogy_service import GenealogyService
    from apps.genealogy.models import Family
    gsvc = GenealogyService()
    clan = request.user.clan
    families = Family.objects.filter(clan=clan).select_related('founding_person')
    
    # Annotate each family with founder and member count
    for f in families:
        f.member_count = f.members.count()
        f.founder = gsvc.get_family_founder(f)
    
    tree_data = None
    ancestors_tree = None
    descendants_tree = None
    selected_person = None
    person_details = None
    selected_member = None
    
    person_pk = person_pk or request.GET.get('person')
    if person_pk:
        try:
            selected_person = Person.objects.get(pk=person_pk)
            # Find the Member associated with this Person (for profile link)
            selected_member = selected_person.memberships.first()
            ancestors = gsvc.get_ancestor_tree(selected_person, depth=4)
            ancestors_tree = json.dumps(ancestors) if ancestors else None
            descendants = gsvc.get_family_tree(selected_person, depth=4)
            descendants_tree = json.dumps(descendants) if descendants else None
            tree_data = descendants_tree
            person_details = gsvc.get_person_details(selected_person)
        except Person.DoesNotExist:
            pass
    
    all_persons = Person.objects.filter(family_memberships__family__clan=clan).distinct()
    return render(request, 'family_tree.html', {
        'families': families,
        'all_persons': all_persons,
        'tree_data': tree_data,
        'ancestors_tree': ancestors_tree,
        'descendants_tree': descendants_tree,
        'selected_person': selected_person,
        'selected_member': selected_member,
        'person_details': person_details,
    })



@secretary_required
def add_family_member_view(request, family_id):
    from apps.genealogy.models import Family, PersonFamilyMembership, Relationship
    from apps.genealogy.constants import FamilyRole
    family = get_object_or_404(Family, id=family_id, clan=request.user.clan)
    current_memberships = PersonFamilyMembership.objects.filter(family=family).select_related('person')
    current_person_ids = current_memberships.values_list('person_id', flat=True)
    available_persons = Person.objects.exclude(id__in=current_person_ids).order_by('full_name')
    if request.method == 'POST':
        person_id = request.POST.get('person_id')
        role = request.POST.get('role', 'member')
        if person_id:
            try:
                person = Person.objects.get(id=person_id)
                PersonFamilyMembership.objects.create(person=person, family=family, role_in_family=role)
                messages.success(request, f"{person.full_name} added to '{family.name}'.")
            except Person.DoesNotExist: messages.error(request, "Invalid person.")
        return redirect('family-tree')
    return render(request, 'forms/add_family_member.html', {
        'family': family, 'current_memberships': current_memberships,
        'available_persons': available_persons, 'family_roles': FamilyRole.choices,
    })


# ══════════════════════════════════════════════
# POSTS (CLAN FEED)
# ══════════════════════════════════════════════


def posts_view(request):
    from apps.identity.models import Post, PostReaction
    clan = request.user.clan
    posts = Post.objects.filter(clan=clan, is_active=True).select_related('author__person').prefetch_related('reactions', 'post_comments__author__person', 'reports')
    if not request.user.is_moderator and not request.user.is_superuser:
        posts = posts.filter(Q(is_hidden_by_reports=False) | Q(author=request.user))
    posts = posts.order_by('-created_at')
    for post in posts: post.my_reaction = post.reactions.filter(member=request.user).first()
    return render(request, 'posts.html', {'posts': posts})



def create_post(request):
    from apps.identity.models import Post
    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        image = request.FILES.get('image')
        video = request.FILES.get('video')
        if not content and not image and not video:
            messages.error(request, "Post cannot be empty.")
            return redirect('posts')
        Post.objects.create(clan=request.user.clan, author=request.user, content=content, image=image, video=video)
        messages.success(request, "Post shared!")
    return redirect('posts')



def edit_post(request, pk):
    from apps.identity.models import Post
    post = get_object_or_404(Post, pk=pk, clan=request.user.clan)
    if request.user != post.author and not request.user.is_superuser:
        messages.error(request, "You can only edit your own posts.")
        return redirect('posts')
    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        if not content: messages.error(request, "Post content cannot be empty."); return redirect('posts')
        post.content = content; post.edited_at = timezone.now(); post.save()
        messages.success(request, "Post updated!"); return redirect(f'/posts/#post-{post.id}')
    return render(request, 'forms/edit_post.html', {'post': post})



def delete_post(request, pk):
    from apps.identity.models import Post
    post = get_object_or_404(Post, pk=pk)
    if request.user == post.author or request.user.is_superuser:
        post.is_active = False; post.save()
        messages.success(request, "Post deleted.")
    else: messages.error(request, "You can only delete your own posts.")
    return redirect('posts')



def react_post(request, pk):
    from apps.identity.models import Post, PostReaction
    post = get_object_or_404(Post, pk=pk, clan=request.user.clan)
    reaction = request.POST.get('reaction', 'like')
    valid_reactions = [r[0] for r in PostReaction.REACTIONS]
    if reaction not in valid_reactions: reaction = 'like'
    existing = PostReaction.objects.filter(post=post, member=request.user).first()
    if existing:
        if existing.reaction == reaction: existing.delete()
        else: existing.reaction = reaction; existing.save()
    else: PostReaction.objects.create(post=post, member=request.user, reaction=reaction)
    return redirect(f'/posts/#post-{post.id}')



def comment_post(request, pk):
    from apps.identity.models import Post, PostComment
    post = get_object_or_404(Post, pk=pk, clan=request.user.clan)
    content = request.POST.get('content', '').strip()
    if content:
        if len(content) > 500: messages.error(request, "Comment must be under 500 characters."); return redirect(f'/posts/#post-{post.id}')
        PostComment.objects.create(post=post, author=request.user, content=content)
        messages.success(request, "Comment added!")
    else: messages.error(request, "Comment cannot be empty.")
    return redirect(f'/posts/#post-{post.id}')



def delete_comment(request, pk):
    from apps.identity.models import PostComment
    comment = get_object_or_404(PostComment, pk=pk)
    if request.user == comment.author or request.user.is_superuser:
        post_id = comment.post.id; comment.delete()
        messages.success(request, "Comment deleted."); return redirect(f'/posts/#post-{post_id}')
    messages.error(request, "You can only delete your own comments.")
    return redirect('posts')



def report_post(request, pk):
    from apps.identity.models import Post, PostReport
    post = get_object_or_404(Post, pk=pk, clan=request.user.clan, is_active=True)
    if post.author == request.user:
        messages.error(request, "You cannot report your own post."); return redirect(f'/posts/#post-{post.id}')
    if PostReport.objects.filter(post=post, reported_by=request.user).exists():
        messages.warning(request, "You have already reported this post."); return redirect(f'/posts/#post-{post.id}')
    if request.method == 'POST':
        reason = request.POST.get('reason', 'other')
        details = request.POST.get('details', '').strip()
        valid_reasons = [r[0] for r in PostReport.REPORT_REASONS]
        if reason not in valid_reasons: reason = 'other'
        report = PostReport.objects.create(post=post, reported_by=request.user, reason=reason, details=details)
        post.report_count = PostReport.objects.filter(post=post, is_resolved=False).count()
        if post.report_count >= Post.REPORT_THRESHOLD and not post.is_hidden_by_reports:
            post.is_hidden_by_reports = True; post.save()
            NotificationService.notify_post_hidden(post)
            notify_moderators(post)
            messages.warning(request, "Post has been automatically hidden due to multiple reports.")
        else: post.save(); messages.success(request, "Post reported. Moderators will review it.")
        notify_moderators_about_report(report)
        return redirect(f'/posts/#post-{post.id}')
    return render(request, 'forms/report_post.html', {'post': post, 'report_reasons': PostReport.REPORT_REASONS})


def notify_moderators(post):
    moderators = Member.objects.filter(clan=post.clan, status='active', clan_roles__role__hierarchy_level__gte=RoleLevel.ELDER, clan_roles__is_active=True).distinct()
    for moderator in moderators:
        if moderator != post.author:
            Notification.objects.create(recipient=moderator, title="Post Hidden by Reports", message=f"A post by {post.author.person.full_name} has been hidden after {post.report_count} reports.", link=f'/posts/#post-{post.id}')
    if post.author not in moderators:
        Notification.objects.create(recipient=post.author, title="Your Post Has Been Hidden", message="Your post has been hidden after multiple reports. Contact a moderator.", link=f'/posts/#post-{post.id}')


def notify_moderators_about_report(report):
    moderators = Member.objects.filter(clan=report.post.clan, status='active', clan_roles__role__hierarchy_level__gte=RoleLevel.ELDER, clan_roles__is_active=True).distinct()
    for moderator in moderators:
        if moderator != report.reported_by:
            Notification.objects.create(recipient=moderator, title="New Post Report", message=f"{report.reported_by.person.full_name} reported a post by {report.post.author.person.full_name} for: {report.get_reason_display()}", link=f'/admin/identity/postreport/')



@elder_required
@moderator_required
def resolve_report(request, pk):
    from apps.identity.models import PostReport
    report = get_object_or_404(PostReport, pk=pk)
    if request.method == 'POST':
        action = request.POST.get('action')
        note = request.POST.get('note', '').strip()
        if action == 'dismiss':
            report.is_resolved = True; report.resolved_by = request.user; report.resolved_at = timezone.now(); report.resolution_note = note; report.save()
            post = report.post
            unresolved_count = PostReport.objects.filter(post=post, is_resolved=False).count()
            if post.is_hidden_by_reports and unresolved_count < Post.REPORT_THRESHOLD:
                post.is_hidden_by_reports = False; post.report_count = unresolved_count; post.save()
                messages.success(request, "Report dismissed and post restored.")
            else: post.report_count = unresolved_count; post.save(); messages.success(request, "Report dismissed.")
        elif action == 'delete_post':
            post = report.post; post.is_active = False; post.save()
            report.is_resolved = True; report.resolved_by = request.user; report.resolved_at = timezone.now(); report.resolution_note = note; report.save()
            messages.success(request, "Post deleted and report resolved.")
    return redirect('posts')


# ══════════════════════════════════════════════
# PDF REPORTS
# ══════════════════════════════════════════════


def download_monthly_pdf(request, period_label):
    from apps.core.pdf.pdf_service import generate_monthly_statement
    buffer = generate_monthly_statement(request.user.clan, period_label)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="bubabi-{period_label}-statement.pdf"'
    return response


def download_owing_pdf(request):
    from apps.core.pdf.pdf_service import generate_owing_list
    buffer = generate_owing_list(request.user.clan)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="bubabi-owing-list.pdf"'
    return response


def download_annual_pdf(request, year):
    from apps.core.pdf.pdf_service import generate_annual_summary
    buffer = generate_annual_summary(request.user.clan, year)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="bubabi-annual-{year}.pdf"'
    return response


def download_member_statement_pdf(request, pk):
    from apps.core.pdf.pdf_service import generate_member_statement
    member = get_object_or_404(Member, pk=pk, clan=request.user.clan)
    buffer = generate_member_statement(member)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="statement-{member.id}.pdf"'
    return response


# ══════════════════════════════════════════════
# SMS FUNCTIONALITY
# ══════════════════════════════════════════════


@secretary_required
@rate_limit("sms_test", 3, 300)
def sms_test_view(request):
    if request.method == 'POST':
        phone = request.POST.get('phone', '').strip()
        sms_message = request.POST.get('message', '').strip()
        if phone and sms_message:
            response = SMSService.send([phone], sms_message)
            if response:
                recipients = response.get('SMSMessageData', {}).get('Recipients', [])
                success_count = sum(1 for r in recipients if r.get('status') == 'Success')
                if success_count > 0: messages.success(request, 'SMS sent successfully!')
                else: messages.warning(request, 'SMS delivery status unclear.')
            else: messages.error(request, 'Failed to send SMS.')
        else: messages.warning(request, 'Please provide phone and message.')
    return redirect('dashboard')


@secretary_required
@rate_limit("sms_bulk", 2, 600)
def send_bulk_sms(request):
    if request.method == 'POST':
        message = request.POST.get('message', '').strip()
        if message:
            try:
                SMSService.send_bulk(request.user.clan, message)
                messages.success(request, "SMS broadcast sent to all active members.")
            except Exception as e: messages.error(request, f"Failed to send SMS: {str(e)}")
        else: messages.error(request, "Message cannot be empty.")
    return redirect('system')


@treasurer_required
def send_contribution_reminder(request, contribution_id):
    contribution = get_object_or_404(Contribution, id=contribution_id, member__clan=request.user.clan)
    if contribution.member.phone:
        try:
            BubabiNotifications.contribution_reminder(contribution)
            messages.success(request, f"Reminder sent to {contribution.member.person.full_name}.")
        except Exception as e: messages.error(request, f"Failed to send reminder: {str(e)}")
    else: messages.warning(request, "Member has no phone number.")
    return redirect('contributions')


# ══════════════════════════════════════════════
# AVATAR UPLOAD
# ══════════════════════════════════════════════


def upload_avatar(request, pk):
    member = get_object_or_404(Member, pk=pk, clan=request.user.clan)
    if request.user != member and not request.user.is_superuser:
        messages.error(request, "You can only change your own profile photo.")
        return redirect('member-profile', pk=pk)
    if request.method == 'POST' and request.FILES.get('photo'):
        if not member.person:
            messages.error(request, "Member has no associated person record.")
            return redirect('member-profile', pk=pk)
        member.person.profile_image = request.FILES['photo']
        member.person.save()
        messages.success(request, "Profile photo updated!")
    return redirect('member-profile', pk=pk)


def remove_avatar(request, pk):
    member = get_object_or_404(Member, pk=pk, clan=request.user.clan)
    if request.user != member and not request.user.is_superuser:
        messages.error(request, "You can only remove your own profile photo.")
        return redirect('member-profile', pk=pk)
    if member.person and member.person.profile_image:
        member.person.profile_image.delete()
        member.person.save()
        messages.success(request, "Profile photo removed.")
    return redirect('member-profile', pk=pk)


# ══════════════════════════════════════════════
# LOAN APPROVAL
# ══════════════════════════════════════════════


@treasurer_required
def review_loan(request, pk):
    loan = get_object_or_404(Loan, pk=pk, borrower__clan=request.user.clan)
    if request.method == 'POST':
        action = request.POST.get('action')
        amount_approved = request.POST.get('amount_approved')
        notes = request.POST.get('notes', '')
        if action == 'approve' and amount_approved:
            loan.amount_approved = amount_approved; loan.status = LoanStatus.APPROVED; loan.save()
            NotificationService.notify_loan_status(loan, 'approved')
            try: BubabiNotifications.loan_status_update(loan)
            except Exception as e: print(f"SMS error: {e}")
            AuditService.log(actor=request.user, action='loan.approved', domain='financial', target=loan, request=request)
            messages.success(request, "Loan approved.")
        elif action == 'reject':
            loan.status = LoanStatus.REJECTED; loan.notes = notes; loan.save()
            NotificationService.notify_loan_status(loan, 'rejected')
            try: BubabiNotifications.loan_status_update(loan)
            except Exception as e: print(f"SMS error: {e}")
            messages.success(request, "Loan rejected.")
        elif action == 'disburse':
            try:
                svc.disburse_loan(loan=loan, disbursed_by=request.user, request=request)
                NotificationService.notify_loan_status(loan, 'disbursed')
                try: BubabiNotifications.loan_status_update(loan)
                except Exception as e: print(f"SMS error: {e}")
                messages.success(request, "Loan disbursed.")
            except Exception as e: messages.error(request, str(e))
        return redirect('loans')
    return render(request, 'forms/loan_review_form.html', {'loan': loan})


# ══════════════════════════════════════════════
# MEETING MINUTES
# ══════════════════════════════════════════════


@secretary_required
def record_minutes(request, event_pk):
    from apps.events.models import ClanEvent, MeetingMinutes, EventAttendance
    from apps.events.forms import MeetingMinutesForm
    event = get_object_or_404(ClanEvent, pk=event_pk, clan=request.user.clan)
    if request.method == 'POST':
        form = MeetingMinutesForm(request.POST)
        if form.is_valid():
            minutes = form.save(commit=False); minutes.event = event; minutes.recorded_by = request.user; minutes.save()
            active_members = Member.objects.filter(clan=request.user.clan, status=MemberStatus.ACTIVE)
            for member in active_members:
                present = request.POST.get(f'attend_{member.id}') == 'on'
                EventAttendance.objects.update_or_create(event=event, member=member, defaults={'present': present})
            messages.success(request, "Minutes recorded.")
            return redirect('events')
    else:
        form = MeetingMinutesForm()
    active_members = Member.objects.filter(clan=request.user.clan, status=MemberStatus.ACTIVE).select_related('person')
    return render(request, 'forms/minutes_form.html', {'form': form, 'event': event, 'members': active_members})


# ══════════════════════════════════════════════
# MODERATOR DASHBOARD
# ══════════════════════════════════════════════


@moderator_required
def moderator_dashboard(request):
    from apps.identity.models import Post, PostReport
    clan = request.user.clan
    pending_reports = PostReport.objects.filter(post__clan=clan, is_resolved=False).select_related('post__author__person', 'reported_by__person').order_by('-created_at')[:20]
    hidden_posts = Post.objects.filter(clan=clan, is_active=True, is_hidden_by_reports=True).select_related('author__person')
    blocked_members = Member.objects.filter(clan=clan, is_blocked=True).select_related('person', 'blocked_by__person')
    suspended_members = Member.objects.filter(clan=clan, status=MemberStatus.SUSPENDED).select_related('person')
    return render(request, 'moderator.html', {
        'clan': clan,
        'pending_reports': pending_reports, 'pending_reports_count': pending_reports.count(),
        'hidden_posts': hidden_posts, 'hidden_posts_count': hidden_posts.count(),
        'blocked_members': blocked_members, 'blocked_count': blocked_members.count(),
        'suspended_members': suspended_members, 'suspended_count': suspended_members.count(),
    })


# ══════════════════════════════════════════════
# CLAN DOCUMENTS & JUDICIAL
# ══════════════════════════════════════════════


def documents_view(request):
    from apps.identity.models import ClanDocument, JudicialCase
    clan = request.user.clan
    documents = ClanDocument.objects.filter(clan=clan, is_active=True, is_public=True).select_related('uploaded_by__person').order_by('-created_at')
    if request.user.is_moderator or request.user.is_superuser:
        cases = JudicialCase.objects.filter(clan=clan)
    else:
        cases = JudicialCase.objects.filter(clan=clan, is_confidential=False)
    cases = cases.select_related('filed_by__person', 'presided_by__person').order_by('-created_at')
    documents_by_type = {}
    for doc in documents:
        type_name = doc.get_document_type_display()
        if type_name not in documents_by_type: documents_by_type[type_name] = []
        documents_by_type[type_name].append(doc)
    return render(request, 'documents.html', {
        'documents': documents, 'documents_by_type': documents_by_type, 'cases': cases,
        'can_upload': request.user.is_moderator or request.user.is_superuser or request.user.clan_roles.filter(is_active=True, role__hierarchy_level__gte=4).exists(),
    })



def upload_document_view(request):
    # Only Moderator (level 4), Leader (level 5), or Super Admin can upload
    can_upload = request.user.is_superuser or request.user.clan_roles.filter(is_active=True, role__hierarchy_level__gte=4).exists()
    if not can_upload:
        messages.error(request, "Only Moderators, Leaders, or Super Admin can upload documents.")
        return redirect('documents')
    
    from apps.identity.models import ClanDocument
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        doc_type = request.POST.get('document_type', 'other')
        description = request.POST.get('description', '').strip()
        version = request.POST.get('version', '1.0')
        is_public = request.POST.get('is_public') == 'on'
        effective_date = request.POST.get('effective_date') or None
        file = request.FILES.get('file')
        if not title or not file:
            messages.error(request, "Title and file are required.")
            return redirect('upload-document')
        ClanDocument.objects.create(clan=request.user.clan, title=title, document_type=doc_type, description=description, file=file, version=version, is_public=is_public, uploaded_by=request.user, effective_date=effective_date)
        messages.success(request, f"Document '{title}' uploaded successfully!")
        return redirect('documents')
    return render(request, 'forms/upload_document.html', {'document_types': ClanDocument.DOCUMENT_TYPES})



def file_judicial_case_view(request):
    from apps.identity.models import JudicialCase
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        case_type = request.POST.get('case_type', 'other')
        description = request.POST.get('description', '').strip()
        parties = request.POST.get('parties_involved', '').strip()
        if not title or not description:
            messages.error(request, "Title and description are required.")
            return redirect('file-case')
        import random
        case_number = f"CASE-{timezone.now().strftime('%Y%m%d')}-{random.randint(100, 999)}"
        attachment = request.FILES.get('attachment')
        JudicialCase.objects.create(clan=request.user.clan, case_number=case_number, title=title, case_type=case_type, description=description, parties_involved=parties, filed_by=request.user, status='pending', attachment=attachment)
        messages.success(request, f"Case #{case_number} filed successfully!")
        return redirect('documents')
    return render(request, 'forms/file_case.html', {'case_types': JudicialCase.CASE_TYPES})



@moderator_required
def update_case_view(request, pk):
    from apps.identity.models import JudicialCase
    case = get_object_or_404(JudicialCase, pk=pk, clan=request.user.clan)
    if not (request.user.is_moderator or request.user.is_superuser):
        messages.error(request, "Only Moderators can update cases.")
        return redirect('documents')
    if request.method == 'POST':
        case.status = request.POST.get('status', case.status)
        case.ruling = request.POST.get('ruling', case.ruling)
        case.presided_by = request.user
        ruling_date = request.POST.get('ruling_date')
        if ruling_date: case.ruling_date = ruling_date
        attachment = request.FILES.get('attachment')
        if attachment: case.attachment = attachment
        case.save()
        messages.success(request, f"Case #{case.case_number} updated!")
        return redirect('documents')
    return render(request, 'forms/update_case.html', {'case': case, 'case_statuses': JudicialCase.CASE_STATUS})


# ══════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════

def _get_upcoming_events(clan):
    from apps.events.models import ClanEvent
    return ClanEvent.objects.filter(clan=clan, is_cancelled=False, scheduled_at__gte=timezone.now()).order_by('scheduled_at')[:5]
# The existing view is good, just ensure it handles all actions properly


@elder_required
@moderator_required
def resolve_all_reports(request):
    """Resolve all pending reports at once."""
    from apps.identity.models import Post, PostReport, Notification
    
    if request.method == 'POST':
        clan = request.user.clan
        reports = PostReport.objects.filter(post__clan=clan, is_resolved=False)
        count = reports.count()
        
        # Resolve all reports
        reports.update(
            is_resolved=True,
            resolved_by=request.user,
            resolved_at=timezone.now(),
            resolution_note='Batch resolved by moderator'
        )
        
        # Restore hidden posts that are now under threshold
        hidden_posts = Post.objects.filter(clan=clan, is_hidden_by_reports=True)
        restored = 0
        for post in hidden_posts:
            unresolved = PostReport.objects.filter(post=post, is_resolved=False).count()
            post.report_count = unresolved
            if unresolved < Post.REPORT_THRESHOLD:
                post.is_hidden_by_reports = False
                restored += 1
            post.save()
        
        messages.success(request, f"Resolved {count} reports. Restored {restored} posts.")
    
    return redirect('moderator')

# ══════════════════════════════════════════════
# PERMISSION AUDIT HELPERS
# ══════════════════════════════════════════════

def can_manage_member(manager, member):
    """Check if manager can manage this member."""
    if manager.is_superuser:
        return True
    if manager == member:
        return False  # Can't manage yourself
    if manager.is_leader:
        return member.clan == manager.clan
    return False

def can_assign_role(granter, role_level):
    """Check if user can assign a role of given level."""
    if granter.is_superuser:
        return True  # Super Admin can assign any role
    if granter.is_leader:
        return role_level < 5  # Leader can assign up to Moderator (level 4)
    return False

def can_moderate_content(user):
    """Check if user can moderate posts/reports."""
    if user.is_superuser:
        return True
    return user.clan_roles.filter(
        is_active=True,
        role__hierarchy_level__gte=RoleLevel.ELDER
    ).exists()


@superuser_required
def payment_methods_view(request):
    """Manage clan payment methods."""
    clan = request.user.clan
    
    # Load current settings from clan.payment_methods JSON
    payment_methods = {}
    if clan and getattr(clan, 'payment_methods', None):
        try:
            import json
            payment_methods = json.loads(clan.payment_methods)
        except:
            pass
    
    from apps.identity.forms import PaymentMethodsForm
    
    if request.method == 'POST':
        form = PaymentMethodsForm(request.POST)
        if form.is_valid():
            # Build payment methods JSON
            methods = {
                'cash_enabled': form.cleaned_data['cash_enabled'],
                'mobile_money_enabled': form.cleaned_data['mobile_money_enabled'],
                'bank_transfer_enabled': form.cleaned_data['bank_transfer_enabled'],
                'default_method': form.cleaned_data['default_method'],
                'mobile_providers': [],
                'banks': [],
            }
            
            # Parse mobile providers
            for line in form.cleaned_data['mobile_providers'].strip().split('\n'):
                line = line.strip()
                if line and '|' in line:
                    parts = line.split('|')
                    if len(parts) >= 2:
                        methods['mobile_providers'].append({
                            'code': parts[0].strip(),
                            'name': parts[1].strip(),
                            'prefixes': parts[2].strip().split(',') if len(parts) > 2 else []
                        })
            
            # Parse banks
            for line in form.cleaned_data['banks'].strip().split('\n'):
                line = line.strip()
                if line and '|' in line:
                    parts = line.split('|')
                    if len(parts) >= 2:
                        methods['banks'].append({
                            'code': parts[0].strip(),
                            'name': parts[1].strip(),
                        })
            
            import json
            clan.payment_methods = json.dumps(methods)
            clan.save()
            messages.success(request, "Payment methods updated successfully!")
            return redirect('payment-methods')
    else:
        # Build initial data from stored JSON
        initial = {}
        if payment_methods:
            initial['cash_enabled'] = payment_methods.get('cash_enabled', True)
            initial['mobile_money_enabled'] = payment_methods.get('mobile_money_enabled', True)
            initial['bank_transfer_enabled'] = payment_methods.get('bank_transfer_enabled', True)
            initial['default_method'] = payment_methods.get('default_method', 'mobile_money')
            
            # Rebuild text areas
            mobile_lines = []
            for p in payment_methods.get('mobile_providers', []):
                mobile_lines.append(f"{p['code']}|{p['name']}|{','.join(p.get('prefixes', []))}")
            initial['mobile_providers'] = '\n'.join(mobile_lines) or "mpesa|M-Pesa (Vodacom)|07,2557\ntigo|Tigo Pesa|071,25571\nairtel|Airtel Money|06,2556\nhalopesa|HaloPesa|062,25562"
            
            bank_lines = []
            for b in payment_methods.get('banks', []):
                bank_lines.append(f"{b['code']}|{b['name']}")
            initial['banks'] = '\n'.join(bank_lines) or "crdb|CRDB Bank\nnmb|NMB Bank\nnbc|NBC Bank\nequity|Equity Bank"
        else:
            initial['mobile_providers'] = "mpesa|M-Pesa (Vodacom)|07,2557\ntigo|Tigo Pesa|071,25571\nairtel|Airtel Money|06,2556\nhalopesa|HaloPesa|062,25562"
            initial['banks'] = "crdb|CRDB Bank\nnmb|NMB Bank\nnbc|NBC Bank\nequity|Equity Bank"
        
        form = PaymentMethodsForm(initial=initial)
    
    return render(request, 'payment_methods.html', {
        'form': form,
        'clan': clan,
        'current_methods': payment_methods,
    })


@superuser_required
def system_cleanup_view(request):
    """System cleanup — delete old data, reset finances, clear test data."""
    from apps.financials.models import Contribution, Fine, Loan, Expense, LedgerEntry, Account
    from apps.identity.models import Post, PostReport, PostComment, PostReaction, Notification, Announcement
    from apps.audit.models import AuditLog
    from apps.events.models import ClanEvent, MeetingMinutes, EventAttendance
    from apps.governance.models import Vote, VoteCast
    from apps.genealogy.models import Relationship, Family
    
    clan = request.user.clan
    results = {}
    
    if request.method == 'POST':
        # Require superuser password for all cleanup actions
        password = request.POST.get('confirm_password', '')
        if not request.user.check_password(password):
            messages.error(request, "❌ Incorrect password. Cleanup actions require your account password for security.")
            return redirect('system-cleanup')
        
        action = request.POST.get('action', '')
        
        # ─── Reset Financial Data ───
        if action == 'reset_finances':
            pool = Account.objects.filter(clan=clan, account_type='pool').first()
            if pool:
                n = LedgerEntry.objects.filter(account=pool).count()
                LedgerEntry.objects.filter(account=pool).delete()
                results['ledger_entries'] = n
            
            # Reset contributions
            n = Contribution.objects.filter(member__clan=clan).count()
            Contribution.objects.filter(member__clan=clan).update(
                amount_paid=0, status='due', verified_by=None,
                payment_method='', payment_ref=''
            )
            results['contributions_reset'] = n
            
            # Delete fines
            n = Fine.objects.filter(member__clan=clan).count()
            Fine.objects.filter(member__clan=clan).delete()
            results['fines_deleted'] = n
            
            # Delete loans
            n = Loan.objects.filter(borrower__clan=clan).count()
            Loan.objects.filter(borrower__clan=clan).delete()
            results['loans_deleted'] = n
            
            # Delete expenses
            n = Expense.objects.filter(clan=clan).count()
            Expense.objects.filter(clan=clan).delete()
            results['expenses_deleted'] = n
            
            messages.success(request, f"Financial data reset: {sum(results.values())} records cleaned.")
        
        # ─── Clear Posts & Feed ───
        elif action == 'clear_posts':
            n = Post.objects.filter(clan=clan).count()
            Post.objects.filter(clan=clan).delete()
            PostReport.objects.filter(post__clan=clan).delete()
            PostComment.objects.filter(post__clan=clan).delete()
            PostReaction.objects.filter(post__clan=clan).delete()
            results['posts_deleted'] = n
            messages.success(request, f"All posts, comments, and reactions deleted ({n} posts).")
        
        # ─── Clear Notifications ───
        elif action == 'clear_notifications':
            n = Notification.objects.filter(recipient__clan=clan).count()
            Notification.objects.filter(recipient__clan=clan).delete()
            results['notifications'] = n
            messages.success(request, f"Deleted {n} notifications.")
        
        # ─── Clear Announcements ───
        elif action == 'clear_announcements':
            n = Announcement.objects.filter(clan=clan).count()
            Announcement.objects.filter(clan=clan).delete()
            results['announcements'] = n
            messages.success(request, f"Deleted {n} announcements.")
        
        # ─── Clear Events ───
        elif action == 'clear_events':
            n = ClanEvent.objects.filter(clan=clan).count()
            MeetingMinutes.objects.filter(event__clan=clan).delete()
            EventAttendance.objects.filter(event__clan=clan).delete()
            ClanEvent.objects.filter(clan=clan).delete()
            results['events'] = n
            messages.success(request, f"Deleted {n} events and related data.")
        
        # ─── Clear Audit Logs ───
        elif action == 'clear_audit':
            n = AuditLog.objects.count()
            AuditLog.objects.all().delete()
            results['audit_logs'] = n
            messages.success(request, f"Deleted {n} audit log entries.")
        
        # ─── Clear Votes ───
        elif action == 'clear_votes':
            n = Vote.objects.filter(clan=clan).count()
            VoteCast.objects.filter(vote__clan=clan).delete()
            Vote.objects.filter(clan=clan).delete()
            results['votes'] = n
            messages.success(request, f"Deleted {n} votes.")
        
        # ─── Clear Media Files ───
        elif action == 'clear_media':
            import os, shutil
            from django.conf import settings
            media_root = settings.MEDIA_ROOT
            deleted_files = 0
            deleted_dirs = 0
            for item in os.listdir(media_root):
                item_path = os.path.join(media_root, item)
                if os.path.isfile(item_path):
                    os.remove(item_path)
                    deleted_files += 1
                elif os.path.isdir(item_path) and item not in ['profiles', 'clan']:
                    shutil.rmtree(item_path)
                    deleted_dirs += 1
            results['files'] = deleted_files
            results['dirs'] = deleted_dirs
            messages.success(request, f"Deleted {deleted_files} files and {deleted_dirs} directories from media.")
        
        # ─── Time-based Cleanup ───
        elif action == 'cleanup_old':
            days = int(request.POST.get('days', 90))
            cutoff = timezone.now() - timezone.timedelta(days=days)
            
            # Old notifications
            n = Notification.objects.filter(recipient__clan=clan, sent_at__lt=cutoff).count()
            Notification.objects.filter(recipient__clan=clan, sent_at__lt=cutoff).delete()
            results['old_notifications'] = n
            
            # Old audit logs
            n = AuditLog.objects.filter(timestamp__lt=cutoff).count()
            AuditLog.objects.filter(timestamp__lt=cutoff).delete()
            results['old_audit'] = n
            
            # Old announcements
            n = Announcement.objects.filter(clan=clan, created_at__lt=cutoff, is_active=False).count()
            Announcement.objects.filter(clan=clan, created_at__lt=cutoff, is_active=False).delete()
            results['old_announcements'] = n
            
            # Old posts (inactive, older than cutoff)
            n = Post.objects.filter(clan=clan, is_active=False, created_at__lt=cutoff).count()
            Post.objects.filter(clan=clan, is_active=False, created_at__lt=cutoff).delete()
            results['old_posts'] = n
            
            messages.success(request, f"Cleaned up data older than {days} days: {sum(results.values())} records.")
        
        return redirect('system-cleanup')
    
    # GET — show current counts
    context = {
        'clan': clan,
        'stats': {
            'contributions': Contribution.objects.filter(member__clan=clan).count(),
            'fines': Fine.objects.filter(member__clan=clan).count(),
            'loans': Loan.objects.filter(borrower__clan=clan).count(),
            'expenses': Expense.objects.filter(clan=clan).count(),
            'ledger': LedgerEntry.objects.filter(account__clan=clan).count(),
            'posts': Post.objects.filter(clan=clan).count(),
            'notifications': Notification.objects.filter(recipient__clan=clan).count(),
            'announcements': Announcement.objects.filter(clan=clan).count(),
            'events': ClanEvent.objects.filter(clan=clan).count(),
            'audit': AuditLog.objects.count(),
            'votes': Vote.objects.filter(clan=clan).count(),
        }
    }
    return render(request, 'system_cleanup.html', context)


@superuser_required
def upload_constitution_view(request):
    """Upload or replace the clan constitution. Super Admin only. Only one active at a time."""
    from apps.identity.models import ClanDocument
    
    clan = request.user.clan
    
    if request.method == 'POST':
        title = request.POST.get('title', f'Constitution of {clan.name}').strip()
        version = request.POST.get('version', '1.0').strip()
        description = request.POST.get('description', f'Constitution of the {clan.name} clan.').strip()
        file = request.FILES.get('file')
        
        if not file:
            messages.error(request, "Please select a file to upload.")
            return redirect('upload-constitution')
        
        # Deactivate any existing constitution
        ClanDocument.objects.filter(
            clan=clan, document_type='constitution', is_active=True
        ).update(is_active=False)
        
        # Upload new constitution
        doc = ClanDocument.objects.create(
            clan=clan,
            title=title,
            document_type='constitution',
            description=description,
            version=version,
            file=file,
            is_public=True,
            uploaded_by=request.user,
            is_active=True
        )
        
        messages.success(request, f"✅ Constitution v{version} uploaded successfully!")
        return redirect('documents')
    
    # Check if there's an existing constitution
    existing = ClanDocument.objects.filter(
        clan=clan, document_type='constitution', is_active=True
    ).first()
    
    return render(request, 'forms/upload_constitution.html', {
        'existing': existing,
        'clan': clan,
    })


@xframe_options_exempt
def view_document(request, pk):
    """Preview a document inline instead of downloading."""
    from apps.identity.models import ClanDocument
    doc = get_object_or_404(ClanDocument, pk=pk, clan=request.user.clan, is_active=True)
    
    # Determine file type
    import mimetypes
    mime_type, _ = mimetypes.guess_type(doc.file.name)
    
        # Read text file content server-side (Django templates cannot call .read())
    file_content = None
    if doc.file.name.lower().endswith((".txt", ".log", ".md", ".csv")):
        try:
            doc.file.open("rb")
            file_content = doc.file.read().decode("utf-8", errors="replace")
            doc.file.close()
        except Exception:
            file_content = None

    context = {
        'document': doc,
        'mime_type': mime_type or 'application/octet-stream',
        'is_image': mime_type and mime_type.startswith('image/'),
        'is_pdf': mime_type == 'application/pdf',
        'is_text': doc.file.name.lower().endswith((".txt", ".log", ".md", ".csv")) or (mime_type and mime_type.startswith('text/')),
        'file_content': file_content,
    }
    return render(request, 'view_document.html', context)




def registration_pending_view(request):
    clan = request.user.clan if request.user.is_authenticated and hasattr(request.user, 'clan') else Clan.objects.first()
    clan_banner = clan.banner_image if clan and clan.banner_image else None
    return render(request, "registration_pending.html", {
        'clan': clan,
        'clan_banner': clan_banner,
    })

def privacy_view(request):
    """Display privacy policy page."""
    return render(request, 'privacy.html')

def terms_view(request):
    """Display terms of service page."""
    return render(request, 'terms.html')


def accept_terms_view(request):
    """Force user to accept terms before using the system."""
    if request.user.has_accepted_terms:
        return redirect('member-dashboard')
    
    if request.method == 'POST':
        request.user.has_accepted_terms = True
        request.user.accepted_terms_at = timezone.now()
        request.user.accepted_terms_ip = request.META.get('REMOTE_ADDR', '')
        request.user.save()
        messages.success(request, "Welcome! You have accepted the terms.")
        return redirect('member-dashboard')
    
    return render(request, 'accept_terms_view.html')
