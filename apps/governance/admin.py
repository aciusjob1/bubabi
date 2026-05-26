from django.contrib import admin
from .models import (
    ClanPermission, Role, MemberRole,
    ApprovalRequest, ApprovalVote,
    Vote, VoteCast
)


@admin.register(ClanPermission)
class ClanPermissionAdmin(admin.ModelAdmin):
    list_display  = ['codename', 'domain', 'description']
    list_filter   = ['domain']
    search_fields = ['codename']


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display  = ['name', 'clan', 'hierarchy_level', 'is_system_role']
    list_filter   = ['clan', 'hierarchy_level', 'is_system_role']
    filter_horizontal = ['permissions']
    readonly_fields   = ['created_at', 'updated_at']


@admin.register(MemberRole)
class MemberRoleAdmin(admin.ModelAdmin):
    list_display  = ['member', 'role', 'assigned_by', 'is_active', 'expires_at']
    list_filter   = ['is_active', 'role']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(ApprovalRequest)
class ApprovalRequestAdmin(admin.ModelAdmin):
    list_display  = ['action_type', 'status', 'initiated_by',
                     'minimum_approvals', 'approval_count']
    list_filter   = ['status', 'action_type']
    readonly_fields = ['created_at', 'updated_at', 'resolved_at']


@admin.register(ApprovalVote)
class ApprovalVoteAdmin(admin.ModelAdmin):
    list_display  = ['request', 'voter', 'vote', 'voted_at']
    readonly_fields = ['voted_at', 'created_at', 'updated_at']


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display  = ['topic', 'clan', 'status', 'quorum_percent',
                     'yes_count', 'no_count', 'closes_at']
    list_filter   = ['status', 'clan']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(VoteCast)
class VoteCastAdmin(admin.ModelAdmin):
    list_display  = ['vote', 'member', 'choice', 'weight', 'cast_at']
    readonly_fields = ['cast_at', 'created_at', 'updated_at']