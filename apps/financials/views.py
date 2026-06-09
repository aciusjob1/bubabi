from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from apps.identity.views import treasurer_required
from apps.financials.models import Loan
from apps.core.decorators import rate_limit

from apps.governance.decorators import permission_required
from apps.financials.forms import (
    RecordPaymentForm, ExpenseForm,
    FineForm, LoanRequestForm,
    CreateContributionForm
)
from apps.financials.constants import ContributionStatus, FineStatus, LoanStatus
from apps.financials.models import Contribution, Fine, Loan, Expense
from apps.financials.services.financial_service import FinancialService
from apps.identity.models import Member, Clan
from apps.identity.constants import MemberStatus

svc = FinancialService()


@login_required
@rate_limit("record_payment", 10, 3600)
def record_payment_view(request, pk):
    # Fraud check: prevent duplicate payments within 60 seconds
    from django.core.cache import cache
    cache_key = f"payment:{pk}"
    if cache.get(cache_key):
        messages.warning(request, "Duplicate payment detected. Please wait before trying again.")
        return redirect("contributions")
    cache.set(cache_key, True, 60)
    contribution = get_object_or_404(
        Contribution, pk=pk, member__clan=request.user.clan
    )
    # Only the member themselves or a treasurer can record payment
    is_treasurer = request.user.clan_roles.filter(is_active=True, role__hierarchy_level__gte=3).exists()
    if not (request.user.is_superuser or is_treasurer or contribution.member == request.user):
        messages.error(request, "You can only record payments for yourself.")
        return redirect('contributions')
    if request.method == 'POST':
        form = RecordPaymentForm(request.POST, user=request.user)
        if form.is_valid():
            try:
                svc.record_contribution_payment(
                    contribution=contribution,
                    amount=form.cleaned_data['amount'],
                    payment_method=form.cleaned_data['payment_method'],
                    payment_ref=form.cleaned_data.get('payment_ref', ''),
                    recorded_by=request.user,
                    request=request
                )
                messages.success(request, "Payment recorded successfully.")
                return redirect('contributions')
            except Exception as e:
                messages.error(request, str(e))
    else:
        form = RecordPaymentForm(initial={'amount': contribution.balance_due}, user=request.user)
    return render(request, 'forms/payment_form.html', {
        'form': form, 'contribution': contribution, 'balance_due': contribution.amount_due - contribution.amount_paid, 'current_user_name': request.user.person.full_name if request.user.person else request.user.email, 'can_use_cash': request.user.is_superuser or request.user.clan_roles.filter(is_active=True, role__hierarchy_level__gte=3).exists()
    })


@login_required
@treasurer_required
def verify_payment_view(request, pk):
    
    contribution = get_object_or_404(
        Contribution, pk=pk, member__clan=request.user.clan
    )
    try:
        svc.verify_contribution(
            contribution=contribution,
            verified_by=request.user,
            request=request
        )
        messages.success(request, "Payment verified.")
    except Exception as e:
        messages.error(request, str(e))
    return redirect('treasurer')


@login_required
@treasurer_required
def add_expense_view(request):
    if request.method == 'POST':
        form = ExpenseForm(request.POST)
        if form.is_valid():
            try:
                svc.record_expense(
                    clan=request.user.clan,
                    description=form.cleaned_data['description'],
                    amount=form.cleaned_data['amount'],
                    category=form.cleaned_data['category'],
                    approved_by=request.user,
                    expense_date=form.cleaned_data['expense_date'],
                    receipt_ref=form.cleaned_data.get('receipt_ref', ''),
                    notes=form.cleaned_data.get('notes', ''),
                    request=request
                )
                messages.success(request, "Expense recorded.")
                return redirect('treasurer')
            except Exception as e:
                messages.error(request, str(e))
    else:
        form = ExpenseForm()
    return render(request, 'forms/expense_form.html', {'form': form})


@login_required
@treasurer_required
def issue_fine_view(request, pk):
    member = get_object_or_404(Member, pk=pk, clan=request.user.clan)
    clan = request.user.clan
    
    if request.method == 'POST':
        form = FineForm(request.POST)
        if form.is_valid():
            try:
                # Use clan default late_fine_amount if no amount specified
                amount = form.cleaned_data.get('amount') or clan.late_fine_amount
                
                svc.issue_fine(
                    member=member,
                    reason=form.cleaned_data['reason'],
                    amount=amount,
                    issued_by=request.user,
                    request=request
                )
                messages.success(
                    request,
                    f"Fine of {clan.currency} {amount:,.0f} issued to {member.person.full_name}."
                )
                return redirect('fines')
            except Exception as e:
                messages.error(request, str(e))
    else:
        # Pre-fill with clan default fine amount
        form = FineForm(initial={
            'amount': clan.late_fine_amount if clan else 10000
        })
    
    return render(request, 'forms/fine_form.html', {
        'form': form,
        'member': member,
        'clan': clan,
    })


@login_required
@rate_limit("loan_request", 3, 3600)
def request_loan_view(request):
    # Fraud check: max 3 active loans
    active_loans = Loan.objects.filter(borrower=request.user, status__in=["approved", "disbursed"]).count()
    if active_loans >= 3:
        messages.error(request, "You have too many active loans. Repay existing loans first.")
        return redirect("loans")
    clan = request.user.clan
    
    if request.method == 'POST':
        form = LoanRequestForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data['amount']
            
            # Validate against clan max_loan_amount
            if clan and clan.max_loan_amount and amount > clan.max_loan_amount:
                messages.error(
                    request,
                    f"Loan amount exceeds clan maximum of {clan.currency} {clan.max_loan_amount:,.0f}."
                )
                return render(request, 'forms/loan_form.html', {
                    'form': form,
                    'clan': clan,
                })
            
            try:
                svc.request_loan(
                    borrower=request.user,
                    amount=amount,
                    purpose=form.cleaned_data['purpose'],
                    request=request
                )
                messages.success(request, "Loan request submitted successfully.")
                return redirect('member-dashboard')
            except Exception as e:
                messages.error(request, str(e))
    else:
        form = LoanRequestForm()
    
    return render(request, 'forms/loan_form.html', {
        'form': form,
        'clan': clan,
    })


@login_required
@permission_required("can_generate_contributions")
def create_contributions_view(request):
    clan = request.user.clan
    
    if request.method == 'POST':
        form = CreateContributionForm(request.POST)
        if form.is_valid():
            created = 0
            skipped = 0
            
            # Use clan default contribution if not specified
            amount_due = form.cleaned_data.get('amount_due') or (
                clan.default_contribution if clan else 50000
            )

            with transaction.atomic():
                for member in Member.objects.filter(
                    clan=clan, status=MemberStatus.ACTIVE
                ):
                    exists = Contribution.objects.filter(
                        member=member,
                        period_label=form.cleaned_data['period_label']
                    ).exists()

                    if not exists:
                        Contribution.objects.create(
                            member=member,
                            amount_due=amount_due,
                            amount_paid=0,
                            due_date=form.cleaned_data['due_date'],
                            period_label=form.cleaned_data['period_label'],
                            status=ContributionStatus.DUE
                        )
                        created += 1
                    else:
                        skipped += 1

            messages.success(
                request,
                f"Created {created} contributions of {clan.currency} {amount_due:,.0f} each. "
                f"Skipped {skipped} (already exist)."
            )
            return redirect('contributions')
    else:
        # Pre-fill with clan default contribution amount
        initial = {}
        if clan:
            initial['amount_due'] = clan.default_contribution
        form = CreateContributionForm(initial=initial)
    
    # Count active members for preview
    active_count = Member.objects.filter(
        clan=clan, status=MemberStatus.ACTIVE
    ).count() if clan else 0
    
    return render(request, 'forms/contribution_form.html', {
        'form': form,
        'active_members_count': active_count,
        'clan': clan,
    })


@login_required
@treasurer_required
def mark_late_contributions_view(request):
    """Manually trigger marking late contributions."""
    try:
        count = svc.mark_late_contributions(request.user.clan, request=request)
        messages.success(request, f"Marked {count} contributions as late.")
    except Exception as e:
        messages.error(request, str(e))
    return redirect('treasurer')
# Replace old decorators with permission-based ones

# Patch: re-decorate create_contributions_view
# This will be applied by updating the decorator stack

@login_required
def repay_loan_view(request, pk):
    """Record a loan repayment."""
    loan = get_object_or_404(Loan, pk=pk, borrower__clan=request.user.clan)
    
    # Only the borrower or treasurer can record repayment
    is_treasurer = request.user.clan_roles.filter(is_active=True, role__hierarchy_level__gte=3).exists()
    if not (request.user.is_superuser or is_treasurer or loan.borrower == request.user):
        messages.error(request, "You can only repay your own loans.")
        return redirect('loans')
    
    if loan.status not in [LoanStatus.DISBURSED, LoanStatus.DEFAULTED]:
        messages.error(request, "This loan is not in a repayable state.")
        return redirect('loans')
    
    remaining = loan.total_due - sum(r.amount for r in loan.repayments.all())
    
    if request.method == 'POST':
        try:
            amount = float(request.POST.get('amount', 0))
            if amount <= 0:
                messages.error(request, "Please enter a valid amount.")
                return redirect('repay-loan', pk=loan.id)
            if amount > remaining:
                messages.error(request, f"Amount exceeds remaining balance of {remaining:,.0f}.")
                return redirect('repay-loan', pk=loan.id)
            
            svc.record_loan_repayment(
                loan=loan,
                amount=amount,
                recorded_by=request.user,
                request=request
            )
            messages.success(request, f"Repayment of {amount:,.0f} recorded successfully!")
            return redirect('loans')
        except Exception as e:
            messages.error(request, str(e))
    
    return render(request, 'forms/repay_loan.html', {
        'loan': loan,
        'remaining': remaining,
        'total_due': loan.total_due,
        'total_repaid': sum(r.amount for r in loan.repayments.all()),
    })
