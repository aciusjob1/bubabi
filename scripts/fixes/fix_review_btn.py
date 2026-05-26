with open('templates/moderator.html', 'r') as f:
    lines = f.readlines()

# Find and fix the broken line
for i, line in enumerate(lines):
    if 'TODO_FIX_LINE_129' in line:
        # This is the correct Review button with media support
        lines[i] = """              <button onclick="openResolveModal('{{ report.id }}', '{{ report.post.content|default:""|truncatechars:200|escapejs }}', '{{ report.post.author.person.full_name|default:report.post.author.email|escapejs }}', '{% if report.post.image and report.post.image.name %}{{ report.post.image.url }}{% endif %}', '{% if report.post.video and report.post.video.name %}{{ report.post.video.url }}{% endif %}', '{% if report.post.image and report.post.image.name %}image{% elif report.post.video and report.post.video.name %}video{% elif report.post.content %}text{% else %}other{% endif %}')" class="action-btn view">📋 {% trans "Review" %}</button>
"""
        print(f"✅ Fixed line {i+1}")
        break

with open('templates/moderator.html', 'w') as f:
    f.writelines(lines)

print("Done!")
