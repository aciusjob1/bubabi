from django.contrib import admin
from .models import (
    Account, LedgerEntry, Contribution,
    Fine, Expense, Loan, LoanRepayment
)


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display  = ['name', 'clan', 'account_type', 'is_active']
    list_filter   = ['account_type', 'clan']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(LedgerEntry)
class LedgerEntryAdmin(admin.ModelAdmin):
    list_display  = ['entry_type', 'amount', 'account',
                     'reference_type', 'is_reversed', 'created_at']
    list_filter   = ['entry_type', 'is_reversed', 'currency']
    search_fields = ['description', 'reference_id']
    readonly_fields = [
        'id', 'created_at', 'entry_type', 'amount',
        'account', 'reference_type', 'reference_id',
        'description', 'created_by', 'is_reversed', 'reversal_of'
    ]

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Contribution)
class ContributionAdmin(admin.ModelAdmin):
    list_display  = ['member', 'period_label', 'amount_due',
                     'amount_paid', 'status', 'due_date']
    list_filter   = ['status', 'payment_method']
    search_fields = ['member__email', 'period_label']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Fine)
class FineAdmin(admin.ModelAdmin):
    list_display  = ['member', 'reason', 'amount', 'status', 'issued_by']
    list_filter   = ['status']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display  = ['description', 'amount', 'category',
                     'approved_by', 'expense_date']
    list_filter   = ['category']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display  = ['borrower', 'amount_requested',
                     'amount_approved', 'status', 'due_date']
    list_filter   = ['status']
    readonly_fields = ['created_at', 'updated_at', 'disbursed_at']


@admin.register(LoanRepayment)
class LoanRepaymentAdmin(admin.ModelAdmin):
    list_display  = ['loan', 'amount', 'recorded_by']
    readonly_fields = ['created_at', 'updated_at']