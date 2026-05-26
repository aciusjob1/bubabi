with open('apps/identity/views.py', 'r') as f:
    content = f.read()

# Update block view permission check
old_block_check = "is_leader = request.user.clan_roles.filter(is_active=True, role__hierarchy_level__gte=RoleLevel.LEADER).exists()\n    if not request.user.is_superuser and not is_leader:\n        messages.error(request, \"Only the Super Admin or Clan Leader can block members.\")"
new_block_check = "is_moderator = request.user.clan_roles.filter(is_active=True, role__hierarchy_level__gte=4).exists()\n    if not request.user.is_superuser and not is_moderator:\n        messages.error(request, \"Only Super Admin, Leader, or Moderator can block members.\")"

content = content.replace(old_block_check, new_block_check)

# Update unblock view permission check
old_unblock_check = "is_leader = request.user.clan_roles.filter(is_active=True, role__hierarchy_level__gte=RoleLevel.LEADER).exists()\n    if not request.user.is_superuser and not is_leader:\n        messages.error(request, \"Only the Super Admin or Clan Leader can unblock members.\")"
new_unblock_check = "is_moderator = request.user.clan_roles.filter(is_active=True, role__hierarchy_level__gte=4).exists()\n    if not request.user.is_superuser and not is_moderator:\n        messages.error(request, \"Only Super Admin, Leader, or Moderator can unblock members.\")"

content = content.replace(old_unblock_check, new_unblock_check)

with open('apps/identity/views.py', 'w') as f:
    f.write(content)

print("✅ Updated permission messages")
