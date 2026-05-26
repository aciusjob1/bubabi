from django.db import models
from apps.core.models import BaseModel, ImmutableModel
from apps.identity.models import Member, Clan
from .constants import (
    AccountType, EntryType, ContributionStatus,
    LoanStatus, FineStatus, PaymentMethod, ExpenseCategory
)


class Account(BaseModel):
    clan         = models.ForeignKey(
                     Clan,
                     on_delete=models.PROTECT,
                     related_name='accounts')
    name         = models.CharField(max_length=255)
    account_type = models.CharField(
                     max_length=20,
                     choices=AccountType.CHOICES)
    description  = models.TextField(blank=True)
    is_active    = models.BooleanField(default=True)

    class Meta:
        unique_together = [('clan', 'name')]

    def __str__(self):
        return f"{self.name} ({self.clan.name})"

    def get_balance(self, as_of=None):
        entries = self.ledger_entries.all()
        if as_of:
            entries = entries.filter(created_at__lte=as_of)
        from django.db.models import Sum
        credits = entries.filter(
            entry_type=EntryType.CREDIT,
            is_reversed=False
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        debits = entries.filter(
            entry_type=EntryType.DEBIT,
            is_reversed=False
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        return credits - debits


class LedgerEntry(ImmutableModel):
    """
    IMMUTABLE. Never update or delete.
    Every financial event creates one of these.
    Corrections = new reversal entry only.
    """
    account        = models.ForeignKey(
                       Account,
                       on_delete=models.PROTECT,
                       related_name='ledger_entries')
    entry_type     = models.CharField(
                       max_length=10,
                       choices=EntryType.CHOICES)
    amount         = models.DecimalField(
                       max_digits=14,
                       decimal_places=2)
    currency = models.CharField(max_length=5, default='TZS')
    reference_type = models.CharField(max_length=50)
    reference_id   = models.CharField(max_length=100)
    description    = models.TextField()
    created_by     = models.ForeignKey(
                       Member,
                       on_delete=models.PROTECT,
                       related_name='ledger_entries_created')
    is_reversed    = models.BooleanField(default=False)
    reversal_of    = models.OneToOneField(
                       'self',
                       null=True, blank=True,
                       on_delete=models.SET_NULL,
                       related_name='reversed_by')

    def __str__(self):
        return (
            f"{self.entry_type.upper()} {self.amount} "
            f"→ {self.account.name} [{self.reference_type}]"
        )


class Contribution(BaseModel):
    member         = models.ForeignKey(
                       Member,
                       on_delete=models.PROTECT,
                       related_name='contributions')
    amount_due     = models.DecimalField(max_digits=14, decimal_places=2)
    amount_paid    = models.DecimalField(
                       max_digits=14,
                       decimal_places=2,
                       default=0)
    due_date       = models.DateField()
    period_label   = models.CharField(max_length=50)
    status         = models.CharField(
                       max_length=20,
                       choices=ContributionStatus.CHOICES,
                       default=ContributionStatus.DUE)
    payment_method = models.CharField(
                       max_length=20,
                       choices=PaymentMethod.CHOICES,
                       null=True, blank=True)
    payment_ref    = models.CharField(
                       max_length=100,
                       blank=True,
                       help_text='Mobile money or bank reference')
    recorded_by    = models.ForeignKey(
                       Member,
                       on_delete=models.PROTECT,
                       related_name='contributions_recorded',
                       null=True, blank=True)
    verified_by    = models.ForeignKey(
                       Member,
                       on_delete=models.PROTECT,
                       related_name='contributions_verified',
                       null=True, blank=True)
    notes          = models.TextField(blank=True)

    class Meta:
        ordering = ['-due_date']

    def __str__(self):
        return (
            f"{self.member} — {self.period_label} "
            f"[{self.status}]"
        )

    @property
    def balance_due(self):
        return self.amount_due - self.amount_paid

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.verified_by and self.recorded_by:
            if self.verified_by == self.recorded_by:
                raise ValidationError(
                    "The person who records a payment "
                    "cannot also verify it."
                )


class Fine(BaseModel):
    member       = models.ForeignKey(
                     Member,
                     on_delete=models.PROTECT,
                     related_name='fines')
    reason       = models.CharField(max_length=255)
    amount       = models.DecimalField(max_digits=14, decimal_places=2)
    issued_by    = models.ForeignKey(
                     Member,
                     on_delete=models.PROTECT,
                     related_name='fines_issued')
    status       = models.CharField(
                     max_length=10,
                     choices=FineStatus.CHOICES,
                     default=FineStatus.UNPAID)
    waived_by    = models.ForeignKey(
                     Member,
                     on_delete=models.PROTECT,
                     related_name='fines_waived',
                     null=True, blank=True)
    linked_contribution = models.ForeignKey(
                     Contribution,
                     on_delete=models.SET_NULL,
                     null=True, blank=True,
                     related_name='fines')

    def __str__(self):
        return f"Fine: {self.member} — {self.amount} [{self.status}]"


class Expense(BaseModel):
    clan             = models.ForeignKey(
                         Clan,
                         on_delete=models.PROTECT,
                         related_name='expenses')
    description      = models.CharField(max_length=255)
    amount           = models.DecimalField(max_digits=14, decimal_places=2)
    category         = models.CharField(
                         max_length=20,
                         choices=ExpenseCategory.CHOICES)
    approved_by      = models.ForeignKey(
                         Member,
                         on_delete=models.PROTECT,
                         related_name='expenses_approved')
    receipt_ref      = models.CharField(max_length=100, blank=True)
    expense_date     = models.DateField()
    notes            = models.TextField(blank=True)

    class Meta:
        ordering = ['-expense_date']

    def __str__(self):
        return f"{self.description} — {self.amount} ({self.expense_date})"


class Loan(BaseModel):
    borrower         = models.ForeignKey(
                         Member,
                         on_delete=models.PROTECT,
                         related_name='loans')
    amount_requested = models.DecimalField(max_digits=14, decimal_places=2)
    amount_approved  = models.DecimalField(
                         max_digits=14,
                         decimal_places=2,
                         null=True, blank=True)
    interest_rate    = models.DecimalField(
                         max_digits=5,
                         decimal_places=2,
                         default=0)
    purpose          = models.TextField()
    status           = models.CharField(
                         max_length=20,
                         choices=LoanStatus.CHOICES,
                         default=LoanStatus.REQUESTED)
    due_date         = models.DateField(null=True, blank=True)
    disbursed_at     = models.DateTimeField(null=True, blank=True)
    notes            = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return (
            f"Loan: {self.borrower} — "
            f"{self.amount_requested} [{self.status}]"
        )

    @property
    def total_due(self):
        if not self.amount_approved:
            return 0
        interest = self.amount_approved * (self.interest_rate / 100)
        return self.amount_approved + interest


class LoanRepayment(BaseModel):
    loan         = models.ForeignKey(
                     Loan,
                     on_delete=models.PROTECT,
                     related_name='repayments')
    amount       = models.DecimalField(max_digits=14, decimal_places=2)
    recorded_by  = models.ForeignKey(
                     Member,
                     on_delete=models.PROTECT,
                     related_name='repayments_recorded')
    ledger_entry = models.ForeignKey(
                     LedgerEntry,
                     on_delete=models.PROTECT,
                     related_name='loan_repayments')
    notes        = models.TextField(blank=True)

    def __str__(self):
        return f"Repayment: {self.loan} — {self.amount}"