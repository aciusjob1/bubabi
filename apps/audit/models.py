from django.db import models
from apps.core.models import ImmutableModel
from apps.identity.models import Member


class AuditLog(ImmutableModel):
    """
    Permanent, immutable record of every significant
    action in the system. Never updated. Never deleted.
    """
    actor       = models.ForeignKey(
                    Member,
                    on_delete=models.SET_NULL,
                    null=True, blank=True,
                    related_name='audit_logs')
    action      = models.CharField(max_length=100)
    domain      = models.CharField(
                    max_length=30,
                    choices=[
                        ('financial',  'Financial'),
                        ('membership', 'Membership'),
                        ('governance', 'Governance'),
                        ('genealogy',  'Genealogy'),
                        ('events',     'Events'),
                        ('system',     'System'),
                    ])
    target_type = models.CharField(max_length=50)
    target_id   = models.CharField(max_length=100)
    before_state = models.JSONField(null=True, blank=True)
    after_state  = models.JSONField(null=True, blank=True)
    reason      = models.TextField(blank=True)
    ip_address  = models.GenericIPAddressField(null=True, blank=True)
    timestamp   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return (
            f"[{self.domain}] {self.action} "
            f"by {self.actor} at {self.timestamp}"
        )