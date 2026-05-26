from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from datetime import timedelta

from apps.events.models import ClanEvent, MeetingMinutes, EventAttendance
from apps.events.forms import EventForm, MeetingMinutesForm
from apps.identity.models import Member
from apps.identity.constants import MemberStatus
from apps.governance.constants import RoleLevel
from apps.audit.services.audit_service import AuditService
from apps.core.sms_service import BubabiNotifications

# ══════════════════════════════════════════════
# PERMISSION HELPERS
# ══════════════════════════════════════════════

def is_secretary_or_above(user):
    """Secretary, Leader, Super Admin can manage events."""
    if user.is_superuser:
        return True
    return user.clan_roles.filter(
        is_active=True,
        role__hierarchy_level__gte=RoleLevel.SECRETARY
    ).exists()

def is_leader_or_above(user):
    """Leader, Super Admin can delete events."""
    if user.is_superuser:
        return True
    return user.clan_roles.filter(
        is_active=True,
        role__hierarchy_level__gte=RoleLevel.LEADER
    ).exists()

# ══════════════════════════════════════════════
# EVENT LIST (All Members)
# ══════════════════════════════════════════════

@login_required
def event_list(request):
    """View all clan events."""
    clan = request.user.clan
    now = timezone.now()
    
    # Upcoming events (not cancelled, in the future)
    upcoming = ClanEvent.objects.filter(
        clan=clan,
        is_cancelled=False,
        scheduled_at__gte=now
    ).order_by('scheduled_at')
    
    # Past events (already happened, not cancelled)
    past = ClanEvent.objects.filter(
        clan=clan,
        is_cancelled=False,
        scheduled_at__lt=now
    ).order_by('-scheduled_at')[:20]
    
    # Ongoing events (started but not ended yet)
    ongoing = ClanEvent.objects.filter(
        clan=clan,
        is_cancelled=False,
        scheduled_at__lte=now,
        end_at__gte=now
    ).order_by('scheduled_at') if hasattr(ClanEvent, 'end_at') else ClanEvent.objects.none()
    
    # Cancelled events
    cancelled = ClanEvent.objects.filter(
        clan=clan,
        is_cancelled=True
    ).order_by('-scheduled_at')[:10]
    
    can_manage = is_secretary_or_above(request.user)
    
    context = {
        'upcoming_events': upcoming,
        'past_events': past,
        'ongoing_events': ongoing if 'ongoing' in dir() else [],
        'cancelled_events': cancelled,
        'can_manage': can_manage,
        'now': now,
    }
    return render(request, 'events/list.html', context)


@login_required
def event_detail(request, pk):
    """View event details and attendance."""
    event = get_object_or_404(ClanEvent, pk=pk, clan=request.user.clan)
    minutes = MeetingMinutes.objects.filter(event=event).first()
    attendance = EventAttendance.objects.filter(event=event).select_related('member__person')
    user_attendance = attendance.filter(member=request.user).first()
    
    can_manage = is_secretary_or_above(request.user)
    
    # Determine event status based on date
    now = timezone.now()
    if event.is_cancelled:
        event_status = 'cancelled'
    elif event.scheduled_at > now:
        event_status = 'upcoming'
    elif hasattr(event, 'end_at') and event.end_at and event.end_at > now:
        event_status = 'ongoing'
    else:
        event_status = 'past'
    
    context = {
        'event': event,
        'event_status': event_status,
        'minutes': minutes,
        'attendance': attendance,
        'user_attendance': user_attendance,
        'can_manage': can_manage,
        'total_attending': attendance.filter(present=True).count(),
        'total_declined': attendance.filter(present=False).count(),
    }
    return render(request, 'events/detail.html', context)


# ══════════════════════════════════════════════
# EVENT MANAGEMENT (Secretary+)
# ══════════════════════════════════════════════

@login_required
def create_event(request):
    """Create a new clan event."""
    if not is_secretary_or_above(request.user):
        messages.error(request, "Only Secretary, Leader, or Super Admin can create events.")
        return redirect('events')
    
    if request.method == 'POST':
        form = EventForm(request.POST)
        if form.is_valid():
            event = form.save(commit=False)
            event.created_by = request.user
            event.clan = request.user.clan
            event.created_by = request.user
            event.save()
            
            # Notify active members
            notify_members_about_event(event)
            
            AuditService.log(
                actor=request.user,
                action='event.created',
                domain='events',
                target=event,
                request=request
            )
            
            messages.success(request, f"Event '{event.title}' created!")
            return redirect('event-detail', pk=event.pk)
    else:
        form = EventForm()
    
    return render(request, 'events/form.html', {
        'form': form,
        'title': 'Create Event',
        'action': 'Create'
    })


@login_required
def edit_event(request, pk):
    """Edit an existing event. Cannot edit past events."""
    event = get_object_or_404(ClanEvent, pk=pk, clan=request.user.clan)
    
    if not is_secretary_or_above(request.user):
        messages.error(request, "Only Secretary, Leader, or Super Admin can edit events.")
        return redirect('event-detail', pk=event.pk)
    
    # Block editing past events
    if event.scheduled_at < timezone.now() and not event.is_cancelled:
        messages.error(request, "Cannot edit a past event.")
        return redirect('event-detail', pk=event.pk)
        messages.error(request, "Only Secretary, Leader, or Super Admin can edit events.")
        return redirect('event-detail', pk=event.pk)
    
    if request.method == 'POST':
        form = EventForm(request.POST, instance=event)
        if form.is_valid():
            form.save()
            
            AuditService.log(
                actor=request.user,
                action='event.updated',
                domain='events',
                target=event,
                request=request
            )
            
            messages.success(request, f"Event '{event.title}' updated!")
            return redirect('event-detail', pk=event.pk)
        else:
            # Form has errors, pass it back
            messages.error(request, "Please fix the errors below.")
    else:
        form = EventForm(instance=event)
    
    return render(request, 'events/form.html', {
        'form': form,
        'event': event,
    })


@login_required
def cancel_event(request, pk):
    """Cancel an event. Cannot cancel past events."""
    event = get_object_or_404(ClanEvent, pk=pk, clan=request.user.clan)
    
    if not is_secretary_or_above(request.user):
        messages.error(request, "Only Secretary, Leader, or Super Admin can cancel events.")
        return redirect('event-detail', pk=event.pk)
    
    # Block cancelling past events
    if event.scheduled_at < timezone.now():
        messages.error(request, "Cannot cancel a past event.")
        return redirect('event-detail', pk=event.pk)
        messages.error(request, "Only Secretary, Leader, or Super Admin can cancel events.")
        return redirect('event-detail', pk=event.pk)
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        event.is_cancelled = True
        event.cancellation_reason = reason or 'No reason provided'
        event.cancelled_by = request.user
        event.cancelled_at = timezone.now()
        event.save()
        
        # Notify members about cancellation
        notify_members_about_cancellation(event)
        
        AuditService.log(
            actor=request.user,
            action='event.cancelled',
            domain='events',
            target=event,
            request=request
        )
        
        messages.success(request, f"Event '{event.title}' cancelled.")
        return redirect('events')
    
    return render(request, 'events/cancel.html', {'event': event})


@login_required
def delete_event(request, pk):
    """Delete an event permanently (Leader+ only)."""
    event = get_object_or_404(ClanEvent, pk=pk, clan=request.user.clan)
    
    if not is_leader_or_above(request.user):
        messages.error(request, "Only Leader or Super Admin can delete events.")
        return redirect('event-detail', pk=event.pk)
    
    if request.method == 'POST':
        title = event.title
        event.delete()
        
        AuditService.log(
            actor=request.user,
            action='event.deleted',
            domain='events',
            target=None,
            request=request,
            details=f'Deleted event: {title}'
        )
        
        messages.success(request, f"Event '{title}' deleted permanently.")
        return redirect('events')
    
    return render(request, 'events/delete.html', {'event': event})


# ══════════════════════════════════════════════
# ATTENDANCE (All Members)
# ══════════════════════════════════════════════

@login_required
def rsvp_event(request, pk):
    """RSVP to an event. Only allowed for upcoming/ongoing events."""
    event = get_object_or_404(ClanEvent, pk=pk, clan=request.user.clan)
    
    # Block RSVP for past or cancelled events
    if event.is_cancelled:
        messages.error(request, "Cannot RSVP to a cancelled event.")
        return redirect('event-detail', pk=event.pk)
    if event.scheduled_at < timezone.now():
        messages.error(request, "Cannot RSVP to a past event.")
        return redirect('event-detail', pk=event.pk)
    
    if request.method == 'POST':
        attending = request.POST.get('attending') == 'yes'
        note = request.POST.get('note', '').strip()
        
        attendance, created = EventAttendance.objects.update_or_create(
            event=event,
            member=request.user,
            defaults={
                'present': attending,
                'notes': note,
                
            }
        )
        
        status = "attending" if attending else "not attending"
        messages.success(request, f"You are now marked as {status}.")
    
    return redirect('event-detail', pk=event.pk)


@login_required
def manage_attendance(request, pk):
    """Manage attendance for an event (Secretary+). Cannot modify past event attendance."""
    event = get_object_or_404(ClanEvent, pk=pk, clan=request.user.clan)
    
    if not is_secretary_or_above(request.user):
        messages.error(request, "Only Secretary, Leader, or Super Admin can manage attendance.")
        return redirect('event-detail', pk=event.pk)
    
    # Block attendance changes for events older than 7 days
    days_since = (timezone.now() - event.scheduled_at).days
    if days_since > 7:
        messages.error(request, f"Cannot modify attendance for events older than 7 days. This event was {days_since} days ago.")
        return redirect('event-detail', pk=event.pk)
        messages.error(request, "Only Secretary, Leader, or Super Admin can manage attendance.")
        return redirect('event-detail', pk=event.pk)
    
    active_members = Member.objects.filter(
        clan=request.user.clan,
        status=MemberStatus.ACTIVE
    ).select_related('person').order_by('person__full_name')
    
    attendance = EventAttendance.objects.filter(event=event)
    attendance_dict = {a.member_id: a for a in attendance}
    
    if request.method == 'POST':
        for member in active_members:
            present = request.POST.get(f'attend_{member.id}') == 'on'
            EventAttendance.objects.update_or_create(
                event=event,
                member=member,
                defaults={'present': present}
            )
        
        messages.success(request, "Attendance updated!")
        return redirect('event-detail', pk=event.pk)
    
    context = {
        'event': event,
        'members': active_members,
        'attendance_dict': attendance_dict,
    }
    return render(request, 'events/attendance.html', context)


# ══════════════════════════════════════════════
# MEETING MINUTES (Secretary+)
# ══════════════════════════════════════════════

@login_required
def record_minutes(request, pk):
    """Record meeting minutes for an event (Secretary+). Only for past/ongoing events."""
    event = get_object_or_404(ClanEvent, pk=pk, clan=request.user.clan)
    
    if not is_secretary_or_above(request.user):
        messages.error(request, "Only Secretary, Leader, or Super Admin can record minutes.")
        return redirect('event-detail', pk=event.pk)
    
    # Block minutes for future events
    if event.scheduled_at > timezone.now():
        messages.error(request, "Cannot record minutes for a future event. Wait until the meeting has started.")
        return redirect('event-detail', pk=event.pk)
        messages.error(request, "Only Secretary, Leader, or Super Admin can record minutes.")
        return redirect('event-detail', pk=event.pk)
    
    # Get active members for attendance
    active_members = Member.objects.filter(
        clan=request.user.clan,
        status=MemberStatus.ACTIVE
    ).select_related('person').order_by('person__full_name')
    
    existing = MeetingMinutes.objects.filter(event=event).first()
    
    if request.method == 'POST':
        # Handle attendance
        for member in active_members:
            present = request.POST.get(f'attend_{member.id}') == 'on'
            EventAttendance.objects.update_or_create(
                event=event,
                member=member,
                defaults={'present': present}
            )
        
        # Handle minutes
        summary = request.POST.get('discussion', '')  # discussion field maps to summary
        decisions = request.POST.get('decisions', '')
        action_items = request.POST.get('action_items', '')
        next_meeting = request.POST.get('next_meeting') or None
        
        if summary:
            minutes, created = MeetingMinutes.objects.update_or_create(
                event=event,
                defaults={
                    'recorded_by': request.user,
                    'summary': summary,
                    'decisions': decisions,
                    'action_items': action_items,
                    'next_meeting': next_meeting,
                }
            )
            messages.success(request, "Minutes saved successfully!")
        else:
            messages.error(request, "Discussion summary is required.")
            return redirect('record-minutes', pk=event.pk)
        
        return redirect('event-detail', pk=event.pk)
    
    # Pre-fill form with existing data
    initial_data = {
        'discussion': existing.summary if existing else '',
        'decisions': existing.decisions if existing else '',
        'action_items': existing.action_items if existing else '',
        'next_meeting': existing.next_meeting.strftime('%Y-%m-%dT%H:%M') if existing and existing.next_meeting else '',
    }
    
    return render(request, 'events/minutes_form.html', {
        'event': event,
        'members': active_members,
        'existing': existing,
        'form': initial_data,  # Pass as dict, not form object
    })


# ══════════════════════════════════════════════
# NOTIFICATION HELPERS
# ══════════════════════════════════════════════

def notify_members_about_event(event):
    """Send notifications about new event."""
    from apps.identity.models import Notification
    
    active_members = Member.objects.filter(
        clan=event.clan,
        status=MemberStatus.ACTIVE
    )
    
    for member in active_members:
        if member != event.created_by:
            Notification.objects.create(
                recipient=member,
                title="New Clan Event",
                message=f"'{event.title}' scheduled for {event.scheduled_at.strftime('%d %b %Y at %H:%M')}",
                link=f'/events/{event.id}/'
            )


def notify_members_about_cancellation(event):
    """Notify members about event cancellation."""
    from apps.identity.models import Notification
    
    active_members = Member.objects.filter(
        clan=event.clan,
        status=MemberStatus.ACTIVE
    )
    
    for member in active_members:
        Notification.objects.create(
            recipient=member,
            title="Event Cancelled",
            message=f"'{event.title}' has been cancelled. Reason: {event.cancellation_reason}",
            link='/events/'
        )


def send_event_reminders(event):
    """Send SMS reminders for upcoming event."""
    try:
        attending = EventAttendance.objects.filter(
            event=event,
            present=True
        ).select_related('member')
        
        members = [a.member for a in attending if a.member.phone]
        
        if members:
            BubabiNotifications.meeting_reminder(event, members)
            return len(members)
    except Exception as e:
        print(f"SMS reminder error: {e}")
    
    return 0

