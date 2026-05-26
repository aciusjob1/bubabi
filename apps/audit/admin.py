from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display  = ['timestamp', 'actor', 'action',
                     'domain', 'target_type', 'target_id']
    list_filter   = ['domain', 'action']
    search_fields = ['actor__email', 'action', 'target_type']
    readonly_fields = [
        'actor', 'action', 'domain', 'target_type',
        'target_id', 'before_state', 'after_state',
        'reason', 'ip_address', 'timestamp', 'created_at'
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False