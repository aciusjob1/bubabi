from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required
from functools import wraps
from apps.governance.rbac_engine import has_permission

def permission_required(perm_codename):
    """Decorator: requires a specific permission to access the view."""
    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if has_permission(request.user, perm_codename):
                return view_func(request, *args, **kwargs)
            raise PermissionDenied(f"You lack the '{perm_codename}' permission.")
        return wrapper
    return decorator

def audit_action(action, resource, perm):
    """Decorator: logs access to AuditLog after successful permission check."""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not has_permission(request.user, perm):
                raise PermissionDenied(f"Access denied: {perm}")
            response = view_func(request, *args, **kwargs)
            from apps.audit.services.audit_service import AuditService
            AuditService.log(
                actor=request.user,
                action=action,
                domain='access',
                target=resource,
                request=request
            )
            return response
        return wrapper
    return decorator
