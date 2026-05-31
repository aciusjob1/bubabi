from django.db.models import Q
from apps.core.pdf.pdf_service import generate_annual_summary
from apps.core.pdf.pdf_service import generate_owing_list
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

from apps.identity.models import Member, Person, Clan, Announcement, AnnouncementComment, Notification, ClanDocument
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

svc = FinancialService()
mem_svc = MembershipService()


# ══════════════════════════════════════════════
# PERMISSION HELPERS
# ══════════════════════════════════════════════

def is_superuser(user):
    return user.is_authenticated and user.is_superuser


def is_leader(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.clan_roles.filter(is_active=True, role__hierarchy_level__gte=RoleLevel.LEADER).exists()


def is_treasurer(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.clan_roles.filter(is_active=True, role__hierarchy_level__gte=RoleLevel.TREASURER).exists()


def is_secretary(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.clan_roles.filter(is_active=True, role__hierarchy_level__gte=RoleLevel.SECRETARY).exists()


def is_moderator(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.clan_roles.filter(is_active=True, role__hierarchy_level__gte=4).exists()


def is_elder_or_above(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.clan_roles.filter(is_active=True, role__hierarchy_level__gte=RoleLevel.ELDER).exists()


superuser_required = user_passes_test(is_superuser, login_url='member-dashboard')
leader_required = user_passes_test(is_leader, login_url='member-dashboard')
treasurer_required = user_passes_test(is_treasurer, login_url='member-dashboard')
secretary_required = user_passes_test(is_secretary, login_url='member-dashboard')
moderator_required = user_passes_test(is_moderator, login_url='member-dashboard')
elder_required = user_passes_test(is_elder_or_above, login_url='member-dashboard')


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
            user = authenticate(request, email=email, password=password)
        elif phone:
            user = authenticate(request, phone=phone, password=password)

        if user:
            if hasattr(user, "has_accepted_terms") and not user.has_accepted_terms and not user.is_superuser:
                login(request, user)
                return redirect("accept-terms")
            if user.is_blocked:
                return render(request, "account_blocked.html", {"reason": user.block_reason}, status=403)
            elif user.status == 'pending':
                login(request, user)
                return redirect('registration-pending')
            elif user.status == 'suspended':
                login(request, user)
                return render(request, "account_suspended.html", {"reason": "Your account has been suspended."}, status=403)
            elif user.status == 'removed':
                return render(request, "account_blocked.html", {"reason": "Your account has been removed."}, status=403)
            else:
                login(request, user)
                from apps.audit.services.audit_service import AuditService
                AuditService.log(actor=user, action='login', domain='auth', target=user, request=request)
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
    if level >= RoleLevel.LEADER:
        return 'dashboard'
    elif level >= 4:
        return 'moderator'
    elif level >= RoleLevel.TREASURER:
        return 'treasurer'
    elif level >= RoleLevel.SECRETARY:
        return 'secretary'
    elif level >= RoleLevel.ELDER:
        return 'elder'
    return 'member-dashboard'


# ══════════════════════════════════════════════
# DASHBOARDS
# ══════════════════════════════════════════════

def home_view(request):
    if not request.user.is_authenticated:
        return redirect('login')
    return redirect(get_role_dashboard(request.user))


@leader_required
def dashboard(request):
    clan = request.user.clan
    from apps.genealogy.models import Family

    user_role = None
    try:
        from apps.identity.models import ClanMembership
        membership = ClanMembership.objects.get(user=request.user, clan=request.user.clan)
        user_role = membership.role
    except:
        pass

    context = {
        'clan': clan,
        'balance': svc.get_clan_balance(clan),
        'active_count': Member.objects.filter(clan=clan, status=MemberStatus.ACTIVE).count(),
        'total_members': Member.objects.filter(clan=clan).count(),
        'family_count': Family.objects.filter(clan=clan).count(),
        'due_count': Contribution.objects.filter(member__clan=clan, status=ContributionStatus.DUE).count(),
        'late_count': Contribution.objects.filter(member__clan=clan, status=ContributionStatus.LATE).count(),
        'unpaid_fines': Fine.objects.filter(member__clan=clan, status=FineStatus.UNPAID).count(),
        'recent_contributions': Contribution.objects.filter(member__clan=clan).select_related('member__person').order_by('-due_date')[:10],
        'recent_audit': AuditLog.objects.select_related('actor__person').order_by('-timestamp')[:8],
        'user_role': user_role,
    }
    return render(request, 'dashboard.html', context)


@treasurer_required
def treasurer_dashboard(request):
    clan = request.user.clan
    today = timezone.now().date()
    late_contributions = list(Contribution.objects.filter(member__clan=clan, status=ContributionStatus.LATE).select_related('member__person'))
    for c in late_contributions:
        c.days_late = (today - c.due_date).days
    paid_count = Contribution.objects.filter(member__clan=clan, status=ContributionStatus.PAID).count()
    due_count = Contribution.objects.filter(member__clan=clan, status=ContributionStatus.DUE).count()
    late_count = Contribution.objects.filter(member__clan=clan, status=ContributionStatus.LATE).count()
    unpaid_fines = Fine.objects.filter(member__clan=clan, status=FineStatus.UNPAID).count()
    loans_outstanding = Loan.objects.filter(borrower__clan=clan, status__in=['approved', 'disbursed']).aggregate(Sum('amount_approved'))['amount_approved__sum'] or 0
    unverified = Contribution.objects.filter(member__clan=clan, status=ContributionStatus.PAID, verified_by__isnull=True).select_related('member__person', 'recorded_by__person')

    user_role = None
    try:
        from apps.identity.models import ClanMembership
        membership = ClanMembership.objects.get(user=request.user, clan=request.user.clan)
        user_role = membership.role
    except:
        pass

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
        'user_role': user_role,
    }
    return render(request, 'treasurer.html', context)




# ══════════════════════════════════════════════
# REPORTS
# ══════════════════════════════════════════════

def reports_view(request):
    if not request.user.is_authenticated:
        return redirect('login')
    
    if not hasattr(request.user, 'clan') or not request.user.clan:
        from django.http import HttpResponseBadRequest
        return HttpResponseBadRequest("User not associated with any clan")
    
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
        'monthly_data': monthly_data,
        'expense_by_category': expense_by_category,
        'total_collected': sum(m['paid'] for m in monthly_data),
        'collection_rate': round(sum(m['paid'] for m in monthly_data) / sum(m['expected'] for m in monthly_data) * 100 if monthly_data and sum(m['expected'] for m in monthly_data) > 0 else 0, 1),
        'balance': svc.get_clan_balance(clan),
    })


# ══════════════════════════════════════════════
# PDF REPORTS
# ══════════════════════════════════════════════


def download_owing_pdf(request):
    buffer = generate_owing_list(request.user.clan)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="bubabi-owing-list.pdf"'
    return response


def download_annual_pdf(request, year):
    buffer = generate_annual_summary(request.user.clan, year)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="bubabi-annual-{year}.pdf"'
    return response

# ══════════════════════════════════════════════
# DOCUMENT MANAGEMENT
# ══════════════════════════════════════════════

@login_required
def documents_view(request):
    user_role = None
    try:
        from apps.identity.models import ClanMembership
        membership = ClanMembership.objects.get(user=request.user, clan=request.user.clan)
        user_role = membership.role
    except:
        pass

    documents = ClanDocument.objects.filter(clan=request.user.clan, is_active=True).order_by('-created_at')

    documents_by_type = {}
    for doc in documents:
        doc_type = doc.document_type
        if doc_type not in documents_by_type:
            documents_by_type[doc_type] = []
        documents_by_type[doc_type].append(doc)

    context = {
        'documents': documents,
        'documents_by_type': documents_by_type,
        'user_role': user_role,
    }
    return render(request, 'documents.html', context)


@login_required
def upload_document_view(request):
    can_upload = request.user.is_superuser or request.user.clan_roles.filter(is_active=True, role__hierarchy_level__gte=4).exists()
    if not can_upload:
        messages.error(request, "Only Moderators, Leaders, or Super Admin can upload documents.")
        return redirect('documents')

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


@xframe_options_exempt
@login_required
def view_document(request, pk):
    from django.shortcuts import get_object_or_404, render
    from django.http import HttpResponseForbidden, HttpResponseNotFound

    if not request.user.is_authenticated:
        return HttpResponseForbidden("Please log in")

    try:
        doc = get_object_or_404(ClanDocument, pk=pk, clan=request.user.clan, is_active=True)
    except AttributeError:
        return HttpResponseForbidden("No clan association")

    if not doc.file or not doc.file.url:
        return HttpResponseNotFound("File not found")

    preview_url = doc.file.url

    if doc.file.name.lower().endswith('.pdf'):
        if '/image/' in preview_url:
            preview_url = preview_url.replace('/image/', '/raw/')
        preview_url = preview_url.split('?')[0]

    file_extension = doc.file.name.split('.')[-1].lower()
    previewable_types = ['pdf', 'jpg', 'jpeg', 'png', 'gif', 'txt', 'md']
    is_previewable = file_extension in previewable_types

    context = {
        'document': doc,
        'preview_url': preview_url,
        'is_previewable': is_previewable,
        'file_extension': file_extension,
        'is_pdf': file_extension == 'pdf',
        'is_image': file_extension in ['jpg', 'jpeg', 'png', 'gif'],
        'is_text': file_extension in ['txt', 'md'],
    }
    return render(request, 'view_document.html', context)


@login_required
def download_document(request, pk):
    from django.shortcuts import get_object_or_404
    from django.http import HttpResponseRedirect, HttpResponseForbidden, HttpResponseNotFound

    if not request.user.is_authenticated:
        return HttpResponseForbidden("Please log in")

    try:
        doc = get_object_or_404(ClanDocument, pk=pk, clan=request.user.clan, is_active=True)
    except AttributeError:
        return HttpResponseForbidden("No clan association")

    if not doc.file or not doc.file.url:
        return HttpResponseNotFound("File not found")

    cloudinary_url = doc.file.url

    if '.pdf' in cloudinary_url.lower():
        base_url = cloudinary_url.split('?')[0]
        if '/image/' in base_url:
            base_url = base_url.replace('/image/', '/raw/')
        download_url = f"{base_url}?fl_attachment=1"
        return HttpResponseRedirect(download_url)

    return HttpResponseRedirect(cloudinary_url)


@login_required
def delete_document(request, pk):
    from django.shortcuts import get_object_or_404, redirect, render
    from django.http import HttpResponseForbidden, JsonResponse
    from django.contrib import messages
    from apps.identity.models import ClanDocument, ClanMembership

    try:
        doc = get_object_or_404(ClanDocument, pk=pk, clan=request.user.clan, is_active=True)
    except AttributeError:
        messages.error(request, "You are not associated with any clan")
        return redirect('documents')

    is_constitution = (doc.document_type == 'constitution' or 'constitution' in doc.title.lower() or doc.title.lower() == 'constitution')

    can_delete = False
    reason = ""

    try:
        membership = ClanMembership.objects.get(user=request.user, clan=request.user.clan)
        user_role = membership.role
    except ClanMembership.DoesNotExist:
        user_role = None

    if is_constitution:
        if request.user.is_superuser or request.user.is_staff or user_role == 'moderator':
            can_delete = True
            reason = "You are a System Administrator or Moderator (Constitution deletion)"
        else:
            messages.error(request, "Only System Administrators and Moderators can delete the Constitution.")
            return redirect('view-document', pk=pk)
    else:
        if doc.uploaded_by == request.user:
            can_delete = True
            reason = "You are the document uploader"
        elif user_role in ['chairman', 'secretary', 'treasurer', 'elder']:
            can_delete = True
            reason = f"You are a clan {user_role}"
        elif request.user.is_superuser or request.user.is_staff:
            can_delete = True
            reason = "You are a system administrator"
        elif user_role == 'moderator' and doc.document_type in ['general', 'announcement']:
            can_delete = True
            reason = "You are a moderator for this document type"

    if not can_delete:
        messages.error(request, f"You don't have permission to delete this document.")
        return redirect('view-document', pk=pk)

    if request.method == 'POST':
        doc_title = doc.title
        doc.is_active = False
        doc.save()
        messages.success(request, f'Document "{doc_title}" has been deleted successfully by {reason}.')
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': f'Document "{doc_title}" deleted'})
        return redirect('documents')

    return render(request, 'confirm_delete_document.html', {
        'document': doc,
        'reason': reason,
        'can_delete': can_delete,
        'is_constitution': is_constitution
    })