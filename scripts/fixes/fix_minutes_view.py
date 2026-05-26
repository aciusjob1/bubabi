with open('apps/events/views.py', 'r') as f:
    content = f.read()

# Find record_minutes function and update it
old_minutes = '''@login_required
def record_minutes(request, pk):
    """Record meeting minutes for an event."""
    event = get_object_or_404(ClanEvent, pk=pk, clan=request.user.clan)
    
    if not is_secretary_or_above(request.user):
        messages.error(request, "Only Secretary, Leader, or Super Admin can record minutes.")
        return redirect('event-detail', pk=event.pk)
    
    existing = MeetingMinutes.objects.filter(event=event).first()
    
    if request.method == 'POST':
        form = MeetingMinutesForm(request.POST, instance=existing)
        if form.is_valid():
            minutes = form.save(commit=False)
            minutes.event = event
            minutes.recorded_by = request.user
            minutes.save()
            
            messages.success(request, "Minutes recorded successfully!")
            return redirect('event-detail', pk=event.pk)
    else:
        form = MeetingMinutesForm(instance=existing)
    
    return render(request, 'events/minutes_form.html', {
        'form': form,
        'event': event,
        'existing': existing
    })'''

new_minutes = '''@login_required
def record_minutes(request, pk):
    """Record meeting minutes for an event (Secretary+)."""
    event = get_object_or_404(ClanEvent, pk=pk, clan=request.user.clan)
    
    if not is_secretary_or_above(request.user):
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
    })'''

content = content.replace(old_minutes, new_minutes)

with open('apps/events/views.py', 'w') as f:
    f.write(content)

print("✅ Minutes view updated to match template")
