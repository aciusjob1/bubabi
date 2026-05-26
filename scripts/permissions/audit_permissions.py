import re

with open('apps/identity/views.py', 'r') as f:
    content = f.read()

# Find all decorated functions
pattern = r'(@[a-z_]+.*?\n)+def (\w+)'
matches = re.findall(pattern, content)

print("=== VIEW PERMISSION AUDIT ===\n")
print(f"{'Function':<35} {'Access Level':<30}")
print("-" * 65)

for decorators, func_name in matches:
    # Determine access level
    if 'superuser_required' in decorators:
        level = "👑 Super Admin Only"
    elif 'leader_required' in decorators:
        level = "👤 Leader+"
    elif 'moderator_required' in decorators:
        level = "🛡️ Moderator+"
    elif 'treasurer_required' in decorators:
        level = "💰 Treasurer+"
    elif 'secretary_required' in decorators:
        level = "📋 Secretary+"
    elif 'elder_required' in decorators:
        level = "👴 Elder+"
    else:
        level = "👥 All Members"
    
    print(f"{func_name:<35} {level:<30}")

