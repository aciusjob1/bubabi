with open('templates/moderator.html', 'r') as f:
    content = f.read()

# Fix the image check
content = content.replace(
    '{% if report.post.image %}\n            <div style="font-size:0.7rem; color:#6366f1;">🖼️ {% trans "Has image" %}</div>',
    '{% if report.post.image and report.post.image.name %}\n            <div style="font-size:0.7rem; color:#6366f1;">🖼️ {% trans "Has image" %}</div>'
)

# Fix the video check
content = content.replace(
    '{% if report.post.video %}\n            <div style="font-size:0.7rem; color:#6366f1;">🎬 {% trans "Has video" %}</div>',
    '{% if report.post.video and report.post.video.name %}\n            <div style="font-size:0.7rem; color:#6366f1;">🎬 {% trans "Has video" %}</div>'
)

with open('templates/moderator.html', 'w') as f:
    f.write(content)

print("✅ Fixed media checks")
