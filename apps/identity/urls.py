from django.urls import path
from . import views

app_name = 'identity'

urlpatterns = [
    # Dashboard & Core
    path('', views.dashboard, name='dashboard'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Reports
    path('reports/', views.reports_view, name='reports'),
    path('reports/owing/', views.download_owing_pdf, name='owing_pdf'),
    path('reports/annual/<int:year>/', views.download_annual_pdf, name='annual_pdf'),
    
    # Clan Settings
    path('settings/', views.clan_settings_view, name='clan_settings'),
    
    # Documents - Using correct view names
    
    # Judicial/Cases
]
