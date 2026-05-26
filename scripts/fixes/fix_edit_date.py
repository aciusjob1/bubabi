with open('apps/events/views.py', 'r') as f:
    content = f.read()

# Find edit_event and ensure it passes instance properly
old_pattern = "form = EventForm(request.POST, instance=event)"
if old_pattern in content:
    print("✅ edit_event uses instance=event correctly")
else:
    print("❌ edit_event might need fixing")

# Check for the form handling
if "form = EventForm(instance=event)" in content:
    print("✅ GET request uses instance=event")
else:
    print("❌ GET request needs instance=event")
