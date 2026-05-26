with open('templates/moderator.html', 'r') as f:
    content = f.read()

# Replace unsafe image checks
content = content.replace(
    '{% if report.post.image %}🖼️ {% trans "Has image" %}{% endif %}',
    '{% if report.post.image and report.post.image.name %}🖼️ {% trans "Has image" %}{% endif %}'
)

content = content.replace(
    '{% if report.post.video %}🎬 {% trans "Has video" %}{% endif %}',
    '{% if report.post.video and report.post.video.name %}🎬 {% trans "Has video" %}{% endif %}'
)

# Also fix the hidden posts section
content = content.replace(
    '{% if post.image %}🖼️ {% endif %}',
    '{% if post.image and post.image.name %}🖼️ {% endif %}'
)

content = content.replace(
    '{% if post.video %}🎬 {% endif %}',
    '{% if post.video and post.video.name %}🎬 {% endif %}'
)

with open('templates/moderator.html', 'w') as f:
    f.write(content)

print("✅ Fixed all media checks")
