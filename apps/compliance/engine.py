from .models import Policy, UserPolicyAcceptance

def get_active_policy(key):
    """Get the currently active policy for a given key."""
    return Policy.objects.filter(key=key, is_active=True).order_by('-effective_at').first()

def has_user_accepted(user, policy):
    """Check if user has accepted the current version of a policy."""
    if not user.is_authenticated:
        return False
    return UserPolicyAcceptance.objects.filter(
        user=user, policy=policy, accepted_version=policy.version
    ).exists()

def must_accept_policy(user, key):
    """Check if user must accept a policy before accessing the system."""
    if not user.is_authenticated or user.is_superuser:
        return False
    policy = get_active_policy(key)
    if not policy:
        return False
    return not has_user_accepted(user, policy)

def accept_policy(user, key, ip=None, ua=None):
    """Record user acceptance of a policy."""
    policy = get_active_policy(key)
    if not policy:
        return None
    return UserPolicyAcceptance.objects.get_or_create(
        user=user, policy=policy, accepted_version=policy.version,
        defaults={'ip_address': ip or '', 'user_agent': ua or ''}
    )
