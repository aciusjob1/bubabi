from django.db import models
from apps.core.models import BaseModel
from apps.identity.models import Member, Clan
from .constants import EventType, ParticipationStatus


class ClanEvent(BaseModel):
    clan          = models.ForeignKey(
                      Clan,
                      on_delete=models.PROTECT,
                      related_name='events')
    title         = models.CharField(max_length=255)
    event_type    = models.CharField(
                      max_length=20,
                      choices=EventType.CHOICES)
    description   = models.TextField(blank=True)
    scheduled_at  = models.DateTimeField()
    location      = models.CharField(max_length=255, blank=True)
    organized_by  = models.ForeignKey(
                      Member,
                      on_delete=models.PROTECT,
                      related_name='events_organized')
    is_cancelled  = models.BooleanField(default=False)
    is_deleted    = models.BooleanField(default=False)

    class Meta:
        ordering = ['-scheduled_at']

    def __str__(self):
        return f"{self.title} ({self.event_type}) — {self.scheduled_at.date()}"


class EventParticipation(BaseModel):
    event       = models.ForeignKey(
                    ClanEvent,
                    on_delete=models.PROTECT,
                    related_name='participations')
    member      = models.ForeignKey(
                    Member,
                    on_delete=models.PROTECT,
                    related_name='event_participations')
    status      = models.CharField(
                    max_length=20,
                    choices=ParticipationStatus.CHOICES,
                    default=ParticipationStatus.INVITED)
    response_at = models.DateTimeField(null=True, blank=True)
    notes       = models.TextField(blank=True)

    class Meta:
        unique_together = [('event', 'member')]

    def __str__(self):
        return f"{self.member} → {self.event.title} [{self.status}]"
        
        
class MeetingMinutes(BaseModel):
    event        = models.OneToOneField(
                    ClanEvent,
                    on_delete=models.PROTECT,
                    related_name='minutes')
    recorded_by  = models.ForeignKey(
                    'identity.Member',
                    on_delete=models.PROTECT,
                    related_name='minutes_recorded')
    summary      = models.TextField()
    decisions    = models.TextField(blank=True)
    action_items = models.TextField(blank=True)
    next_meeting = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Minutes — {self.event.title}"


class EventAttendance(BaseModel):
    event   = models.ForeignKey(
                ClanEvent,
                on_delete=models.PROTECT,
                related_name='attendance')
    member  = models.ForeignKey(
                'identity.Member',
                on_delete=models.PROTECT,
                related_name='attendance_records')
    present = models.BooleanField(default=False)
    notes   = models.TextField(blank=True)

    class Meta:
        unique_together = [('event', 'member')]