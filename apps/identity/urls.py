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
    path('documents/', views.documents_view, name='documents'),
    path('documents/upload/', views.upload_document_view, name='upload-document'),
    path('documents/<uuid:pk>/', views.view_document, name='view-document'),
    path('documents/<uuid:pk>/download/', views.view_document, name='download-document'),
    
    # Judicial/Cases
    path('judicial/', views.file_judicial_case_view, name='judicial'),
    path('judicial/<int:pk>/', views.update_case_view, name='update-case'),
    
    # Constitution
    path('constitution/', views.upload_constitution_view, name='constitution'),
    
    # Terms & Privacy
    path('terms/', views.terms_view, name='terms'),
    path('privacy/', views.privacy_view, name='privacy'),
    path('accept-terms/', views.accept_terms_view, name='accept-terms'),
    
    # Family Tree
    path('family-tree/', views.family_tree_view, name='family-tree'),
    path('family-tree/add/', views.add_family_member_view, name='add-family-member'),
    
    # Posts/Forum
    path('posts/', views.posts_view, name='posts'),
    path('posts/create/', views.create_post, name='create-post'),
    path('posts/<int:pk>/edit/', views.edit_post, name='edit-post'),
    path('posts/<int:pk>/delete/', views.delete_post, name='delete-post'),
    path('posts/<int:pk>/react/', views.react_post, name='react-post'),
    path('posts/<int:pk>/comment/', views.comment_post, name='comment-post'),
    
    # Announcements
    path('announcements/', views.announcements_view, name='announcements'),
    path('announcements/create/', views.create_announcement, name='create-announcement'),
    path('announcements/<int:pk>/', views.announcement_detail, name='announcement-detail'),
    path('announcements/<int:pk>/delete/', views.delete_announcement, name='delete-announcement'),
    
    # Notifications
    path('notifications/', views.notifications_view, name='notifications'),
    path('notifications/<int:pk>/read/', views.mark_notification_read, name='mark-notification-read'),
    path('notifications/read-all/', views.mark_all_notifications_read, name='mark-all-read'),
]
