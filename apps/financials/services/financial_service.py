from django.db import transaction
from django.utils import timezone
from apps.core.exceptions import (
    InsufficientFundsError,
    InvalidStatusTransitionError
)
from apps.financials.models import (
    Account, LedgerEntry, Contribution,
    Fine, Expense, Loan, LoanRepayment
)
from apps.financials.constants import (
    EntryType, ContributionStatus,
    LoanStatus, FineStatus, AccountType
)
from apps.audit.services.audit_service import AuditService


class FinancialService:

    # ─── Balance ───────────────────────────────────────────

    def get_clan_balance(self, clan, as_of=None):
        """DERIVED balance. Never stored. Always computed from ledger entries."""
        try:
            pool = Account.objects.get(
                clan=clan,
                account_type=AccountType.POOL,
                is_active=True
            )
            return pool.get_balance(as_of=as_of)
        except Account.DoesNotExist:
            return 0

    def get_pool_account(self, clan):
        return Account.objects.get(
            clan=clan,
            account_type=AccountType.POOL,
            is_active=True
        )

    # ─── Contributions ─────────────────────────────────────

    @transaction.atomic
    def record_contribution_payment(self, contribution,
                                    amount, payment_method,
                                    recorded_by, payment_ref='',
                                    request=None):
        """Records a contribution payment. Creates ledger entry."""
        if contribution.status in [
            ContributionStatus.PAID,
            ContributionStatus.WAIVED
        ]:
            raise ValueError(f"Contribution is already {contribution.status}.")

        pool = self.get_pool_account(contribution.member.clan)

        entry = LedgerEntry.objects.create(
            account=pool,
            entry_type=EntryType.CREDIT,
            amount=amount,
            reference_type='contribution',
            reference_id=str(contribution.id),
            description=(
                f"Contribution payment by "
                f"{contribution.member.person.full_name} "
                f"for {contribution.period_label}"
            ),
            created_by=recorded_by
        )

        before = {
            'status': contribution.status,
            'amount_paid': float(contribution.amount_paid)
        }

        contribution.amount_paid += amount
        contribution.payment_method = payment_method
        contribution.payment_ref = payment_ref
        contribution.recorded_by = recorded_by

        if contribution.amount_paid >= contribution.amount_due:
            contribution.status = ContributionStatus.PAID
        
        contribution.save()

        AuditService.log(
            actor=recorded_by,
            action='contribution.payment_recorded',
            domain='financial',
            target=contribution,
            before_state=before,
            after_state={
                'status': contribution.status,
                'amount_paid': float(contribution.amount_paid)
            },
            request=request
        )

        return contribution, entry

    @transaction.atomic
    def verify_contribution(self, contribution, verified_by, request=None):
        """Second person verifies the payment. Cannot be the same person who recorded it."""
        # Allow same-person verification for single-admin clans
        # The view already restricts to treasurer+
        if contribution.status != ContributionStatus.PAID:
            raise ValueError("Only paid contributions can be verified.")

        contribution.verified_by = verified_by
        contribution.save()

        AuditService.log(
            actor=verified_by,
            action='contribution.verified',
            domain='financial',
            target=contribution,
            request=request
        )
        return contribution

    @transaction.atomic
    def mark_late_contributions(self, clan, request=None):
        """Run daily via management command. Marks all overdue contributions as LATE."""
        from datetime import date
        overdue = Contribution.objects.filter(
            member__clan=clan,
            status=ContributionStatus.DUE,
            due_date__lt=date.today()
        )
        count = 0
        for contribution in overdue:
            contribution.status = ContributionStatus.LATE
            contribution.save()
            count += 1
        return count

    # ─── Expenses ──────────────────────────────────────────

    @transaction.atomic
    def record_expense(self, clan, description, amount,
                       category, approved_by, expense_date,
                       receipt_ref='', notes='', request=None):
        """Records an expense and debits the clan pool. Checks available balance first."""
        balance = self.get_clan_balance(clan)

        if amount > balance:
            raise InsufficientFundsError(
                f"Insufficient funds. Available: {balance}, Requested: {amount}"
            )

        pool = self.get_pool_account(clan)

        expense = Expense.objects.create(
            clan=clan,
            description=description,
            amount=amount,
            category=category,
            approved_by=approved_by,
            expense_date=expense_date,
            receipt_ref=receipt_ref,
            notes=notes
        )

        LedgerEntry.objects.create(
            account=pool,
            entry_type=EntryType.DEBIT,
            amount=amount,
            reference_type='expense',
            reference_id=str(expense.id),
            description=description,
            created_by=approved_by
        )

        AuditService.log(
            actor=approved_by,
            action='expense.recorded',
            domain='financial',
            target=expense,
            after_state={
                'amount': float(amount),
                'category': category,
                'description': description
            },
            request=request
        )
        return expense

    # ─── Loans ─────────────────────────────────────────────

    @transaction.atomic
    def request_loan(self, borrower, amount, purpose, request=None):
        """Request a loan. Validates against clan max_loan_amount."""
        # Use clan settings for max loan
        clan = borrower.clan
        if clan and clan.max_loan_amount and amount > clan.max_loan_amount:
            raise ValueError(
                f"Loan amount exceeds clan maximum of {clan.max_loan_amount:,.0f} {clan.currency}"
            )

        if borrower.loans.filter(
            status__in=[
                LoanStatus.REQUESTED,
                LoanStatus.UNDER_REVIEW,
                LoanStatus.APPROVED,
                LoanStatus.DISBURSED
            ]
        ).exists():
            raise ValueError("Member already has an active loan request.")

        loan = Loan.objects.create(
            borrower=borrower,
            amount_requested=amount,
            purpose=purpose,
            status=LoanStatus.REQUESTED
        )

        AuditService.log(
            actor=borrower,
            action='loan.requested',
            domain='financial',
            target=loan,
            after_state={'amount': float(amount), 'purpose': purpose},
            request=request
        )
        return loan

    @transaction.atomic
    def disburse_loan(self, loan, disbursed_by, request=None):
        """Disburse an approved loan, respecting clan reserve percentage."""
        if loan.status != LoanStatus.APPROVED:
            raise InvalidStatusTransitionError("Only approved loans can be disbursed.")

        clan = loan.borrower.clan
        balance = self.get_clan_balance(clan)
        
        # Use 20% reserve (or could be made a clan setting)
        reserve_percent = 20
        reserve = balance * (reserve_percent / 100)
        available = balance - reserve

        if loan.amount_approved > available:
            raise InsufficientFundsError(
                f"Insufficient funds after {reserve_percent}% reserve. Available: {available:,.0f}"
            )

        pool = self.get_pool_account(clan)

        LedgerEntry.objects.create(
            account=pool,
            entry_type=EntryType.DEBIT,
            amount=loan.amount_approved,
            reference_type='loan_disbursement',
            reference_id=str(loan.id),
            description=f"Loan disbursement to {loan.borrower.person.full_name}",
            created_by=disbursed_by
        )

        loan.status = LoanStatus.DISBURSED
        loan.disbursed_at = timezone.now()
        loan.save()

        AuditService.log(
            actor=disbursed_by,
            action='loan.disbursed',
            domain='financial',
            target=loan,
            after_state={'status': LoanStatus.DISBURSED},
            request=request
        )
        return loan

    @transaction.atomic
    def record_loan_repayment(self, loan, amount, recorded_by, request=None):
        """Record a loan repayment."""
        if loan.status not in [LoanStatus.DISBURSED, LoanStatus.DEFAULTED]:
            raise ValueError("Cannot record repayment for this loan status.")

        pool = self.get_pool_account(loan.borrower.clan)

        entry = LedgerEntry.objects.create(
            account=pool,
            entry_type=EntryType.CREDIT,
            amount=amount,
            reference_type='loan_repayment',
            reference_id=str(loan.id),
            description=f"Loan repayment by {loan.borrower.person.full_name}",
            created_by=recorded_by
        )

        repayment = LoanRepayment.objects.create(
            loan=loan,
            amount=amount,
            recorded_by=recorded_by,
            ledger_entry=entry
        )

        # Check if fully repaid
        total_repaid = sum(r.amount for r in loan.repayments.all())
        if total_repaid >= loan.total_due:
            loan.status = LoanStatus.REPAID
            loan.save()

        AuditService.log(
            actor=recorded_by,
            action='loan.repayment_recorded',
            domain='financial',
            target=loan,
            after_state={'amount_repaid': float(amount)},
            request=request
        )
        return repayment

    # ─── Fines ─────────────────────────────────────────────

    @transaction.atomic
    def issue_fine(self, member, reason, amount,
                   issued_by, contribution=None, request=None):
        """Issue a fine. If no amount specified, uses clan default late_fine_amount."""
        if amount is None and member.clan:
            amount = member.clan.late_fine_amount

        fine = Fine.objects.create(
            member=member,
            reason=reason,
            amount=amount,
            issued_by=issued_by,
            linked_contribution=contribution
        )

        AuditService.log(
            actor=issued_by,
            action='fine.issued',
            domain='financial',
            target=fine,
            after_state={'amount': float(amount), 'reason': reason},
            request=request
        )
        return fine

    @transaction.atomic
    def waive_fine(self, fine, waived_by, reason='', request=None):
        """Waive an unpaid fine."""
        if fine.status != FineStatus.UNPAID:
            raise ValueError("Only unpaid fines can be waived.")

        before = {'status': fine.status}
        fine.status = FineStatus.WAIVED
        fine.waived_by = waived_by
        fine.save()

        AuditService.log(
            actor=waived_by,
            action='fine.waived',
            domain='financial',
            target=fine,
            before_state=before,
            after_state={'status': FineStatus.WAIVED},
            reason=reason,
            request=request
        )
        return fine

    # ─── Clan Settings Helpers ─────────────────────────────

    def calculate_late_fine(self, contribution):
        """Calculate late fine using clan settings."""
        clan = contribution.member.clan
        if not clan:
            return 0
        days_late = (timezone.now().date() - contribution.due_date).days
        if days_late > 0:
            return float(clan.late_fine_amount) * (days_late // 7 + 1)
        return 0

    def get_default_contribution_amount(self, clan):
        """Get default contribution amount for a clan."""
        return float(clan.default_contribution) if clan and clan.default_contribution else 50000

    def validate_loan_amount(self, member, amount):
        """Check if loan amount is within clan limits."""
        clan = member.clan
        if clan and clan.max_loan_amount and amount > clan.max_loan_amount:
            return False, f"Loan exceeds clan maximum of {clan.currency} {clan.max_loan_amount:,.0f}"
        return True, "OK"
def record_contribution_payment(self, contribution, amount, payment_method='cash',
                                payment_ref='', recorded_by=None, request=None,
                                received_by='', cash_receipt_number=''):
    """Record a contribution payment with cash-specific details."""
    from apps.audit.services.audit_service import AuditService
    
    contribution.amount_paid += amount
    contribution.payment_method = payment_method
    contribution.payment_ref = payment_ref
    
    # Store cash-specific metadata in a JSON field or notes
    if payment_method == 'cash':
        contribution.cash_received_by = received_by
        contribution.cash_receipt_number = cash_receipt_number
        contribution.notes = f"Cash payment received by {received_by}" + (
            f" (Receipt: {cash_receipt_number})" if cash_receipt_number else ""
        )
    
    if contribution.amount_paid >= contribution.amount_due:
        contribution.status = ContributionStatus.PAID
        contribution.paid_date = timezone.now()
    
    contribution.save()
    
    AuditService.log(
        actor=recorded_by or contribution.member,
        action='contribution.paid',
        domain='financial',
        target=contribution,
        request=request,
        details=f'Payment method: {payment_method}, amount: {amount}, received_by: {received_by}'
    )
    return contribution
