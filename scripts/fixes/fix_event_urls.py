with open('config/urls.py', 'r') as f:
    content = f.read()

# Fix the import line - remove it since we'll use include
content = content.replace(
    "from apps.events import views as event_views\n",
    ""
)

# Fix all direct event URL patterns to use include
old_patterns = [
    "    path('events/',          event_views.events_list_view, name='events'),\n",
    "    path('events/create/',                   event_views.create_event_view,   name='create-event'),\n",
    "    path('events/<uuid:event_pk>/minutes/',  web_views.record_minutes,        name='record-minutes'),\n",
]

for old in old_patterns:
    content = content.replace(old, "")

# Add include for events URLs
# Find the line after the last path import
if "path('events/', include('apps.events.urls'))" not in content:
    # Add after the moderator URL
    content = content.replace(
        "    path('moderator/',  web_views.moderator_dashboard, name='moderator'),\n",
        "    path('moderator/',  web_views.moderator_dashboard, name='moderator'),\n    path('events/', include('apps.events.urls')),\n"
    )

# Make sure include is imported
if "from django.urls import path, include" not in content:
    content = content.replace(
        "from django.urls import path",
        "from django.urls import path, include"
    )

with open('config/urls.py', 'w') as f:
    f.write(content)

print("✅ Event URLs fixed")
