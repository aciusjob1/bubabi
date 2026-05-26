from django.urls import path
from apps.events import views

urlpatterns = [
    path('', views.event_list, name='events'),
    path('create/', views.create_event, name='create-event'),
    path('<uuid:pk>/', views.event_detail, name='event-detail'),
    path('<uuid:pk>/edit/', views.edit_event, name='edit-event'),
    path('<uuid:pk>/cancel/', views.cancel_event, name='cancel-event'),
    path('<uuid:pk>/delete/', views.delete_event, name='delete-event'),
    path('<uuid:pk>/rsvp/', views.rsvp_event, name='rsvp-event'),
    path('<uuid:pk>/attendance/', views.manage_attendance, name='manage-attendance'),
    path('<uuid:pk>/minutes/', views.record_minutes, name='record-minutes'),
]
