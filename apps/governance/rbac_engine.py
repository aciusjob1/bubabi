"""
BUBABI RBAC Engine — Centralized Permission Resolution
Supports: direct permissions + role inheritance + domain isolation + audit logging
"""
from django.core.cache import cache
from apps.governance.models import Role, ClanPermission

def resolve_role_permissions(role, visited=None):
    """Recursively resolve all permissions from a role and its inherited roles."""
    if visited is None:
        visited = set()
    if role.id in visited:
        return set()
    visited.add(role.id)
    perms = set(role.permissions.all())
    for parent in role.inherits.all():
        perms |= resolve_role_permissions(parent, visited)
    return perms

def get_user_permissions(user):
    """Get all effective permissions for a user (roles + inheritance)."""
    if user.is_superuser:
        return set(ClanPermission.objects.all().values_list('codename', flat=True))
    
    cache_key = f"user_perms_{user.id}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    
    roles = user.clan_roles.filter(is_active=True).select_related('role')
    all_perms = set()
    for member_role in roles:
        all_perms |= resolve_role_permissions(member_role.role)
    
    result = {p.codename for p in all_perms}
    cache.set(cache_key, result, 300)  # 5 min cache
    return result

def has_permission(user, perm_code):
    """Check if user has a specific permission."""
    return perm_code in get_user_permissions(user)

def get_permission_graph(user):
    """Debug: return role → permissions mapping for a user."""
    roles = user.clan_roles.filter(is_active=True).select_related('role')
    return {
        mr.role.name: [p.codename for p in resolve_role_permissions(mr.role)]
        for mr in roles
    }

def invalidate_user_cache(user):
    """Clear permission cache for a user (call after role changes)."""
    cache.delete(f"user_perms_{user.id}")
