from django.urls import path
from . import views

urlpatterns = [
    path('balance/',
         views.clan_balance,
         name='api-balance'),

    path('contributions/',
         views.ContributionListView.as_view(),
         name='api-contribution-list'),

    path('contributions/mine/',
         views.MyContributionsView.as_view(),
         name='api-my-contributions'),

    path('contributions/<uuid:pk>/pay/',
         views.record_payment,
         name='api-record-payment'),

    path('loans/',
         views.LoanListView.as_view(),
         name='api-loan-list'),

    path('loans/request/',
         views.request_loan,
         name='api-loan-request'),

    path('fines/',
         views.FineListView.as_view(),
         name='api-fine-list'),

    path('expenses/',
         views.ExpenseListView.as_view(),
         name='api-expense-list'),
]