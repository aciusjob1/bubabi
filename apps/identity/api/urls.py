from django.urls import path
from . import views

urlpatterns = [
    path('me/',
         views.me,
         name='api-me'),

    path('persons/',
         views.PersonListCreateView.as_view(),
         name='api-person-list'),

    path('persons/<uuid:pk>/',
         views.PersonDetailView.as_view(),
         name='api-person-detail'),

    path('members/',
         views.MemberListView.as_view(),
         name='api-member-list'),

    path('members/<uuid:pk>/',
         views.MemberDetailView.as_view(),
         name='api-member-detail'),

    path('members/<uuid:pk>/history/',
         views.MemberHistoryView.as_view(),
         name='api-member-history'),

    path('members/invite/',
         views.invite_member,
         name='api-member-invite'),

    path('members/<uuid:pk>/transition/',
         views.transition_member_status,
         name='api-member-transition'),
]