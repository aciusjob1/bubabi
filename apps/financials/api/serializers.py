from rest_framework import serializers
from apps.financials.models import (
    Account, Contribution, Fine, Expense, Loan
)


class BalanceSerializer(serializers.Serializer):
    balance      = serializers.DecimalField(max_digits=14, decimal_places=2)
    currency     = serializers.CharField()
    as_of        = serializers.DateTimeField()


class ContributionSerializer(serializers.ModelSerializer):
    member_name  = serializers.CharField(
        source='member.person.full_name', read_only=True
    )
    balance_due  = serializers.ReadOnlyField()

    class Meta:
        model  = Contribution
        fields = [
            'id', 'member', 'member_name',
            'amount_due', 'amount_paid', 'balance_due',
            'due_date', 'period_label', 'status',
            'payment_method', 'payment_ref',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'status']


class RecordPaymentSerializer(serializers.Serializer):
    amount         = serializers.DecimalField(max_digits=14, decimal_places=2)
    payment_method = serializers.CharField()
    payment_ref    = serializers.CharField(required=False, default='')


class FineSerializer(serializers.ModelSerializer):
    member_name = serializers.CharField(
        source='member.person.full_name', read_only=True
    )

    class Meta:
        model  = Fine
        fields = [
            'id', 'member', 'member_name',
            'reason', 'amount', 'status',
            'issued_by', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'status']


class ExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Expense
        fields = [
            'id', 'description', 'amount',
            'category', 'approved_by',
            'expense_date', 'receipt_ref',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class LoanSerializer(serializers.ModelSerializer):
    borrower_name = serializers.CharField(
        source='borrower.person.full_name', read_only=True
    )
    total_due = serializers.ReadOnlyField()

    class Meta:
        model  = Loan
        fields = [
            'id', 'borrower', 'borrower_name',
            'amount_requested', 'amount_approved',
            'interest_rate', 'purpose', 'status',
            'due_date', 'disbursed_at', 'total_due',
            'created_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'status', 'disbursed_at'
        ]