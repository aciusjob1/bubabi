from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

# Core
from apps.core import views as core_views

# Identity
from apps.identity import views as identity_views
from apps.identity import views_documents
from apps.identity.views_terms import accept_terms_view
from apps.identity.views_auditor import auditor_dashboard

# Genealogy
from apps.genealogy import views as genealogy_views

# Governance
from apps.governance import views as governance_views

# Financials
from apps.financials import views as financials_views

urlpatterns = [
    path('', include('apps.identity.urls')),
    path('robots.txt', lambda r: __import__('django.http', fromlist=['HttpResponse']).HttpResponse(
        open('static/robots.txt').read(), content_type='text/plain'
    )),
    # Admin
    path('admin/', admin.site.urls),
    
    # About
    path('about/', core_views.about_view, name='about'),
    
    # Authentication
    path('login/', identity_views.login_view, name='login'),
    path('logout/', identity_views.logout_view, name='logout'),
    path('register/', identity_views.register_view, name='register'),
    path('registration-pending/', identity_views.registration_pending_view, name='registration-pending'),
    
    # Dashboards
    path('', identity_views.home_view, name='home'),
    path('dashboard/', identity_views.dashboard, name='dashboard'),
    path('treasurer/', identity_views.treasurer_dashboard, name='treasurer'),
    path('secretary/', identity_views.secretary_dashboard, name='secretary'),
    path('elder/', identity_views.elder_dashboard, name='elder'),
    path('member/', identity_views.member_dashboard, name='member-dashboard'),
    path('moderator/', identity_views.moderator_dashboard, name='moderator'),
    path('system/', identity_views.system_dashboard, name='system'),
    
    # Members
    path('members/', identity_views.members_view, name='members'),
    path('members/invite/', identity_views.invite_member_view, name='invite-member'),
    path('members/<uuid:pk>/', identity_views.member_profile, name='member-profile'),
    path('members/<uuid:pk>/change-status/', identity_views.change_member_status, name='change-member-status'),
    path('members/<uuid:pk>/upload-avatar/', identity_views.upload_avatar, name='upload-avatar'),
    path('members/<uuid:pk>/remove-avatar/', identity_views.remove_avatar, name='remove-avatar'),
    
    # Blocked Members
    path('members/blocked/', identity_views.blocked_members_view, name='blocked-members'),
    path('members/<uuid:pk>/block/', identity_views.block_member_view, name='block-member'),
    path('members/<uuid:pk>/unblock/', identity_views.unblock_member_view, name='unblock-member'),
    
    # Role Assignments
    path('members/<uuid:pk>/assign-leader/', identity_views.assign_leader_view, name='assign-leader'),
    path('members/<uuid:pk>/assign-elder/', identity_views.assign_elder_view, name='assign-elder'),
    path('members/<uuid:pk>/assign-moderator/', identity_views.assign_moderator_view, name='assign-moderator'),
    path('members/<uuid:pk>/assign-treasurer/', identity_views.assign_treasurer_view, name='assign-treasurer'),
    path('members/<uuid:pk>/assign-secretary/', identity_views.assign_secretary_view, name='assign-secretary'),
    
    # Genealogy (family-tree is the main name templates expect)
    path('families/', genealogy_views.family_list_view, name='family-tree'),
    path('families/add/', genealogy_views.add_family_view, name='add-family'),
    path('families/<uuid:family_id>/', genealogy_views.family_detail_view, name='family-detail'),
    path('families/<uuid:family_id>/add-member/', genealogy_views.add_family_member_view, name='add-family-member'),
    path('families/<uuid:family_id>/remove-member/', genealogy_views.remove_family_member_view, name='remove-family-member'),
    path('person/<uuid:person_id>/', genealogy_views.person_genealogy_view, name='person-genealogy'),
    path('person/add/', identity_views.add_person, name='add-person'),
    path('relationships/add/', genealogy_views.add_relationship_view, name='add-relationship'),
    path('relationships/<uuid:relationship_id>/delete/', genealogy_views.delete_relationship_view, name='delete-relationship'),
    
    # Governance
    path('votes/', governance_views.create_vote_view, name='create-vote'),
    path('votes/<uuid:vote_pk>/cast/', governance_views.cast_vote_view, name='cast-vote'),
    path('roles/assign/', governance_views.assign_role_view, name='assign-role'),
    path('approvals/', governance_views.approval_list_view, name='approvals'),
    
    # Financials
    path('contributions/', identity_views.contributions_view, name='contributions'),
    path('contributions/create/', financials_views.create_contributions_view, name='create-contributions'),
    path('contributions/mark-late/', financials_views.mark_late_contributions_view, name='mark-late'),
    path('payments/record/', financials_views.record_payment_view, name='record-payment'),
    path('payments/<uuid:pk>/verify/', financials_views.verify_payment_view, name='verify-payment'),
    path('loans/', identity_views.loans_view, name='loans'),
    path('loans/request/', financials_views.request_loan_view, name='request-loan'),
    path('loans/<uuid:pk>/review/', identity_views.review_loan, name='review-loan'),
    path('fines/', identity_views.fines_view, name='fines'),
    path('fines/issue/', financials_views.issue_fine_view, name='issue-fine'),
    path('expenses/add/', financials_views.add_expense_view, name='add-expense'),
    path('payment-methods/', identity_views.payment_methods_view, name='payment-methods'),
    
    # Events
    path('events/', include('apps.events.urls')),
    
    # Announcements
    path('announcements/', identity_views.announcements_view, name='announcements'),
    path('announcements/create/', identity_views.create_announcement, name='create-announcement'),
    path('announcements/<uuid:pk>/', identity_views.announcement_detail, name='announcement-detail'),
    path('announcements/<uuid:pk>/delete/', identity_views.delete_announcement, name='delete-announcement'),
    
    # Posts
    path('posts/', identity_views.posts_view, name='posts'),
    path('posts/create/', identity_views.create_post, name='create-post'),
    path('posts/<uuid:pk>/edit/', identity_views.edit_post, name='edit-post'),
    path('posts/<uuid:pk>/delete/', identity_views.delete_post, name='delete-post'),
    path('posts/<uuid:pk>/react/', identity_views.react_post, name='react-post'),
    path('posts/<uuid:pk>/comment/', identity_views.comment_post, name='comment-post'),
    path('comments/<uuid:pk>/delete/', identity_views.delete_comment, name='delete-comment'),
    path('posts/<uuid:pk>/report/', identity_views.report_post, name='report-post'),
    path('reports/<uuid:pk>/resolve/', identity_views.resolve_report, name='resolve-report'),
    
    # Notifications
    path('notifications/', identity_views.notifications_view, name='notifications'),
    path('notifications/<uuid:pk>/mark-read/', identity_views.mark_notification_read, name='notif-read'),
    path('notifications/mark-all-read/', identity_views.mark_all_notifications_read, name='mark-all-notifications-read'),
    
    # Documents
    path('documents/', identity_views.documents_view, name='documents'),
    path('documents/upload/', identity_views.upload_document_view, name='upload-document'),
    path('documents/<uuid:pk>/', views_documents.view_document, name='view-document'),
    path('documents/<uuid:pk>/download/', views_documents.download_document, name='download-document'),
    path('documents/<uuid:pk>/delete/', views_documents.delete_document, name='delete-document'),
    path('documents/<uuid:pk>/stream/', views_documents.stream_document, name='stream-document'),
    path('constitution/upload/', identity_views.upload_constitution_view, name='upload-constitution'),
    
    # Judicial Cases
    path('cases/', identity_views.file_judicial_case_view, name='file-case'),
    path('cases/<uuid:pk>/update/', identity_views.update_case_view, name='update-case'),
    
    # Reports (PDF)
    path('reports/', identity_views.reports_view, name='reports'),
    path('reports/monthly/', identity_views.download_monthly_pdf, name='pdf-monthly'),
    path('reports/owing/', identity_views.download_owing_pdf, name='pdf-owing'),
    path('reports/annual/<int:year>/', identity_views.download_annual_pdf, name='pdf-annual'),
    path('reports/member-statement/<uuid:pk>/', identity_views.download_member_statement_pdf, name='pdf-member-statement'),
    
    # SMS
    path('sms/test/', identity_views.sms_test_view, name='sms-test'),
    path('sms/bulk/', identity_views.send_bulk_sms, name='send-bulk-sms'),
    path('sms/reminder/<uuid:contribution_id>/', identity_views.send_contribution_reminder, name='send-contribution-reminder'),
    
    # Audit
    path('audit/', identity_views.audit_view, name='audit'),
    path('auditor/', auditor_dashboard, name='auditor'),
    
    # Legal
    path('privacy/', identity_views.privacy_view, name='privacy'),
    path('terms/', identity_views.terms_view, name='terms'),
    path('accept-terms/', accept_terms_view, name='accept-terms'),
    
    # Settings
    path('settings/clan/', identity_views.clan_settings_view, name='clan-settings'),
    path('system-cleanup/', identity_views.system_cleanup_view, name='system-cleanup'),
    
    # i18n
    path('i18n/', include('django.conf.urls.i18n')),
    
    # API
    path('api/', include('apps.api.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
