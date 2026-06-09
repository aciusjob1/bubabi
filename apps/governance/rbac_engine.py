"""
Role-Based Access Control (RBAC) Engine
"""
from apps.governance.models import ClanPermission, MemberRole


def has_permission(user, perm_codename, resource=None):
    """
    Check if user has a specific permission.
    """
    if not user or not user.is_authenticated:
        return False
    
    if user.is_superuser:
        return True
    
    roles = MemberRole.objects.filter(
        member=user,
        is_active=True,
        expires_at__isnull=True
    ).select_related('role__permissions').prefetch_related('role__inherits__permissions')
    
    if not roles.exists():
        return False
    
    for member_role in roles:
        role = member_role.role
        
        if role.permissions.filter(codename=perm_codename).exists():
            return True
        
        for inherited_role in role.inherits.all():
            if inherited_role.permissions.filter(codename=perm_codename).exists():
                return True
    
    return False


def get_user_permissions(user):
    """Get all permissions for a user."""
    permissions = set()
    
    if user.is_superuser:
        return set(
            ClanPermission.objects.values_list('codename', flat=True)
        )
    
    roles = MemberRole.objects.filter(
        member=user,
        is_active=True
    ).select_related('role').prefetch_related('role__permissions', 'role__inherits__permissions')
    
    for member_role in roles:
        role = member_role.role
        permissions.update(
            role.permissions.values_list('codename', flat=True)
        )
        for inherited_role in role.inherits.all():
            permissions.update(
                inherited_role.permissions.values_list('codename', flat=True)
            )
    
    return permissions
