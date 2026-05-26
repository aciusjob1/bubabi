with open('apps/events/views.py', 'r') as f:
    content = f.read()

# Fix the event save to match actual fields
content = content.replace(
    'event = form.save(commit=False)',
    'event = form.save(commit=False)\n            event.created_by = request.user'
)

with open('apps/events/views.py', 'w') as f:
    f.write(content)

print("✅ Views fixed")
