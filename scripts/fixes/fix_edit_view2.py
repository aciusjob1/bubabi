with open('apps/events/views.py', 'r') as f:
    content = f.read()

# Find edit_event and ensure proper context
old_edit = '''    if request.method == 'POST':
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
        form = EventForm(instance=event)
    
    return render(request, 'events/form.html', {
        'form': form,
        'event': event,
        'title': 'Edit Event',
        'action': 'Update'
    })'''

new_edit = '''    if request.method == 'POST':
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
    })'''

content = content.replace(old_edit, new_edit)

# Also fix create_event similarly
old_create = '''    if request.method == 'POST':
        form = EventForm(request.POST)
        if form.is_valid():
            event = form.save(commit=False)
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
    })'''

new_create = '''    if request.method == 'POST':
        form = EventForm(request.POST)
        if form.is_valid():
            event = form.save(commit=False)
            event.clan = request.user.clan
            event.created_by = request.user
            event.save()
            
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
            messages.error(request, "Please fix the errors below.")
    else:
        form = EventForm()
    
    return render(request, 'events/form.html', {
        'form': form,
    })'''

content = content.replace(old_create, new_create)

with open('apps/events/views.py', 'w') as f:
    f.write(content)

print("✅ Edit/Create views updated")
