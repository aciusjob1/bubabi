from django.utils import timezone
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from apps.financials.models import Contribution, Fine, Expense, Loan
from apps.financials.services.financial_service import FinancialService
from .serializers import (
    ContributionSerializer, RecordPaymentSerializer,
    FineSerializer, ExpenseSerializer, LoanSerializer
)

svc = FinancialService()


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def clan_balance(request):
    clan    = request.user.clan
    balance = svc.get_clan_balance(clan)
    return Response({
        'balance':  balance,
        'currency': 'GHS',
        'as_of':    timezone.now()
    })


class ContributionListView(generics.ListAPIView):
    serializer_class   = ContributionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Contribution.objects.filter(
            member__clan=self.request.user.clan
        ).select_related('member__person')


class MyContributionsView(generics.ListAPIView):
    serializer_class   = ContributionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Contribution.objects.filter(
            member=self.request.user
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def record_payment(request, pk):
    serializer = RecordPaymentSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST
        )
    try:
        contribution = Contribution.objects.get(
            pk=pk,
            member__clan=request.user.clan
        )
        updated, entry = svc.record_contribution_payment(
            contribution=contribution,
            amount=serializer.validated_data['amount'],
            payment_method=serializer.validated_data['payment_method'],
            payment_ref=serializer.validated_data.get('payment_ref', ''),
            recorded_by=request.user,
            request=request
        )
        return Response(ContributionSerializer(updated).data)
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


class LoanListView(generics.ListAPIView):
    serializer_class   = LoanSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Loan.objects.filter(
            borrower__clan=self.request.user.clan
        ).select_related('borrower__person')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def request_loan(request):
    try:
        loan = svc.request_loan(
            borrower=request.user,
            amount=request.data.get('amount'),
            purpose=request.data.get('purpose', ''),
            request=request
        )
        return Response(
            LoanSerializer(loan).data,
            status=status.HTTP_201_CREATED
        )
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


class FineListView(generics.ListAPIView):
    serializer_class   = FineSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Fine.objects.filter(
            member__clan=self.request.user.clan
        )


class ExpenseListView(generics.ListAPIView):
    serializer_class   = ExpenseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Expense.objects.filter(
            clan=self.request.user.clan
        )