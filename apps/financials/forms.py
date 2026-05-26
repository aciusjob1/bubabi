from django import forms
from apps.financials.models import Contribution, Expense, Fine, Loan
from apps.financials.constants import (
    PaymentMethod, ExpenseCategory, ContributionStatus
)


class RecordPaymentForm(forms.Form):
    PAYMENT_CHOICES = [
        ('cash', '💵 Cash'),
        ('mobile_money', '📱 Mobile Money (M-Pesa/Tigo Pesa)'),
        ('bank_transfer', '🏦 Bank Transfer'),
        ('other', '📋 Other'),
    ]
    
    amount = forms.DecimalField(
        max_digits=14, decimal_places=2,
        widget=forms.NumberInput(attrs={'placeholder': '0.00'})
    )
    payment_method = forms.ChoiceField(choices=PAYMENT_CHOICES)
    payment_ref = forms.CharField(required=False, widget=forms.TextInput(attrs={'placeholder': 'Transaction ID or reference'}))
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user:
            from apps.governance.constants import RoleLevel
            is_treasurer = self.user.clan_roles.filter(
                is_active=True, role__hierarchy_level__gte=RoleLevel.TREASURER
            ).exists() or self.user.is_superuser
            if not is_treasurer:
                # Remove cash option for non-treasurers
                self.fields['payment_method'].choices = [
                    ('mobile_money', '📱 Mobile Money (M-Pesa/Tigo Pesa)'),
                    ('bank_transfer', '🏦 Bank Transfer'),
                    ('other', '📋 Other'),
                ]

    payment_method = forms.ChoiceField(
        choices=PaymentMethod.CHOICES
    )
    payment_ref = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Mobile money / bank reference'
        })
    )


class CreateContributionForm(forms.Form):
    period_label = forms.CharField(
        widget=forms.TextInput(attrs={'placeholder': 'e.g. June 2026'})
    )
    amount_due = forms.DecimalField(
        max_digits=14, decimal_places=2,
        widget=forms.NumberInput(attrs={'placeholder': '0.00'})
    )
    due_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'})
    )


class ExpenseForm(forms.ModelForm):
    class Meta:
        model  = Expense
        fields = [
            'description', 'amount',
            'category', 'expense_date',
            'receipt_ref', 'notes'
        ]
        widgets = {
            'description':  forms.TextInput(attrs={
                'placeholder': 'What was this expense for?'
            }),
            'amount':       forms.NumberInput(attrs={
                'placeholder': '0.00'
            }),
            'expense_date': forms.DateInput(attrs={
                'type': 'date'
            }),
            'receipt_ref':  forms.TextInput(attrs={
                'placeholder': 'Receipt or reference number'
            }),
            'notes':        forms.Textarea(attrs={
                'rows': 2,
                'placeholder': 'Additional notes'
            }),
        }


class FineForm(forms.Form):
    member_id = forms.UUIDField(widget=forms.HiddenInput())
    reason    = forms.CharField(
        widget=forms.TextInput(attrs={'placeholder': 'Reason for fine'})
    )
    amount    = forms.DecimalField(
        max_digits=14, decimal_places=2,
        widget=forms.NumberInput(attrs={'placeholder': '0.00'})
    )


class LoanRequestForm(forms.Form):
    amount = forms.DecimalField(
        max_digits=14, decimal_places=2,
        widget=forms.NumberInput(attrs={'placeholder': '0.00'})
    )
    purpose = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': 'What is this loan for?'
        })
    )
# Enhanced RecordPaymentForm with cash details
class RecordPaymentForm(forms.ModelForm):
    class Meta:
        model = Contribution
        fields = ['amount', 'payment_method', 'payment_ref']
    
    amount = forms.DecimalField(min_value=0, max_digits=12, decimal_places=2)
    payment_method = forms.ChoiceField(choices=[
        ('cash', '💵 Cash'),
        ('mobile_money', '📱 Mobile Money'),
        ('bank', '🏦 Bank Transfer'),
        ('other', '📄 Other'),
    ])
    payment_ref = forms.CharField(max_length=100, required=False)
    received_by = forms.CharField(max_length=100, required=False, 
                                  help_text="Name of person who received the cash")
    cash_receipt_number = forms.CharField(max_length=50, required=False,
                                          help_text="Receipt or voucher number")
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        # Make cash fields optional by default
        self.fields['received_by'].required = False
        self.fields['cash_receipt_number'].required = False
