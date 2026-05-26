from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Person, Clan, Member, MemberStatusHistory

@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display   = ['full_name', 'gender', 'birth_date', 'is_deceased']
    list_filter    = ['gender']
    search_fields  = ['full_name']
    readonly_fields = ['created_at', 'updated_at']




@admin.register(Clan)
class ClanAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'code', 'motto', 'is_public',
        'default_contribution', 'currency', 'created_at'
    ]
    search_fields = ['name', 'code']
    list_filter = ['is_public', 'currency']


@admin.register(Member)
class MemberAdmin(UserAdmin):
    list_display  = ['email', 'person', 'clan', 'status', 'is_staff']
    list_filter   = ['status', 'clan']
    search_fields = ['email']
    ordering      = ['email']
    readonly_fields = ['created_at', 'updated_at', 'invited_at']

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal', {'fields': ('person', 'clan', 'phone', 'status')}),
        ('Tracking', {'fields': ('invited_by', 'invited_at', 'joined_at')}),
        ('Permissions', {'fields': (
            'is_staff', 'is_active', 'is_superuser',
            'groups', 'user_permissions'
        )}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'status'),
        }),
    )


@admin.register(MemberStatusHistory)
class MemberStatusHistoryAdmin(admin.ModelAdmin):
    list_display    = ['member', 'from_status', 'to_status', 'changed_by', 'timestamp']
    readonly_fields = ['timestamp', 'created_at', 'updated_at']