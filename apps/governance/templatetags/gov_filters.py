from django import template
from apps.governance.rbac_engine import has_permission

register = template.Library()

@register.simple_tag(takes_context=True)
def has_perm(context, perm_codename):
    """Check if current user has a specific permission (with inheritance)."""
    user = context['request'].user
    if not user.is_authenticated:
        return False
    return has_permission(user, perm_codename)

@register.simple_tag(takes_context=True)
def can(context, perm_codename):
    """Alias for has_perm — shorter syntax."""
    return has_perm(context, perm_codename)
