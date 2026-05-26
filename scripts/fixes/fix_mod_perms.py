with open('apps/identity/views.py', 'r') as f:
    content = f.read()

# Fix block_member_view - allow Leader AND Moderator
content = content.replace(
    '@leader_required\ndef block_member_view',
    '@moderator_required\ndef block_member_view'
)

# Fix unblock_member_view - allow Leader AND Moderator
content = content.replace(
    '@leader_required\ndef unblock_member_view',
    '@moderator_required\ndef unblock_member_view'
)

with open('apps/identity/views.py', 'w') as f:
    f.write(content)

print("✅ Moderator can now block/unblock members")
