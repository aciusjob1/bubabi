with open('templates/moderator.html', 'r') as f:
    content = f.read()

# Find and replace the review button line
old_line = '<button onclick="openResolveModal'
new_button = '''              <button onclick="openResolveModal('{{ report.id }}', '{{ report.post.content|default:""|truncatechars:200|escapejs }}', '{{ report.post.author.person.full_name|default:report.post.author.email|escapejs }}', '{% if report.post.image and report.post.image.name %}{{ report.post.image.url }}{% endif %}', '{% if report.post.video and report.post.video.name %}{{ report.post.video.url }}{% endif %}', '{% if report.post.image and report.post.image.name %}image{% elif report.post.video and report.post.video.name %}video{% elif report.post.content %}text{% else %}other{% endif %}')" class="action-btn view">📋 {% trans "Review" %}</button>'''

# Replace the old line with new one
lines = content.split('\n')
for i, line in enumerate(lines):
    if 'openResolveModal' in line and 'button' in line:
        lines[i] = new_button
        print(f"Fixed line {i+1}")
        break

content = '\n'.join(lines)

with open('templates/moderator.html', 'w') as f:
    f.write(content)

print("✅ Review button restored with media support")
