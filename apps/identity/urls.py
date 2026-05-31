from django.urls import path
from . import views
from .views import (
    dashboard_view, reports_view, clan_settings_view,
    documents_view, upload_document, view_document,
    delete_document, download_document
)

app_name = 'identity'

urlpatterns = [
    # Dashboard & Core
    path('', dashboard_view, name='dashboard'),
    path('dashboard/', dashboard_view, name='dashboard'),
    
    # Reports
    path('reports/', reports_view, name='reports'),
    path('reports/owing/', views.download_owing_pdf, name='owing_pdf'),
    path('reports/annual/<int:year>/', views.download_annual_pdf, name='annual_pdf'),
    
    # Clan Settings
    path('settings/', clan_settings_view, name='clan_settings'),
    
    # Documents
    path('documents/', documents_view, name='documents'),
    path('documents/upload/', upload_document, name='upload-document'),
    path('documents/<uuid:pk>/', view_document, name='view-document'),
    path('documents/<uuid:pk>/delete/', delete_document, name='delete-document'),
    path('documents/<uuid:pk>/download/', download_document, name='download-document'),
    
    # Alternative download path (for compatibility)
    path('download-document/<uuid:pk>/', download_document, name='download-document-alt'),
]
