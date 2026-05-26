from django.contrib import admin
from .models import ClanEvent, EventParticipation


@admin.register(ClanEvent)
class ClanEventAdmin(admin.ModelAdmin):
    list_display  = ['title', 'event_type', 'clan',
                     'scheduled_at', 'organized_by', 'is_cancelled']
    list_filter   = ['event_type', 'is_cancelled', 'clan']
    search_fields = ['title']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(EventParticipation)
class EventParticipationAdmin(admin.ModelAdmin):
    list_display  = ['member', 'event', 'status', 'response_at']
    list_filter   = ['status']
    readonly_fields = ['created_at', 'updated_at']