from apps.audit.models import AuditLog


class AuditService:
    """
    Call this from any other service to record an action.
    Never call AuditLog.objects.create() directly elsewhere.
    Always go through this service.
    """

    @staticmethod
    def log(actor, action, domain, target,
            before_state=None, after_state=None,
            reason='', request=None):
        """
        actor       → Member performing the action
        action      → string e.g. 'loan.approved'
        domain      → 'financial', 'membership', etc.
        target      → the model instance being acted on
        before_state → dict snapshot before change
        after_state  → dict snapshot after change
        reason      → optional explanation
        request     → Django request (for IP logging)
        """
        ip = None
        if request:
            ip = AuditService._get_ip(request)

        AuditLog.objects.create(
            actor=actor,
            action=action,
            domain=domain,
            target_type=target.__class__.__name__,
            target_id=str(target.pk),
            before_state=before_state,
            after_state=after_state,
            reason=reason,
            ip_address=ip,
        )

    @staticmethod
    def _get_ip(request):
        forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if forwarded:
            return forwarded.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')