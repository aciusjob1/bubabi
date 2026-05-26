from django.db import models
from apps.core.models import BaseModel
from apps.identity.models import Member, Clan
from .constants import (
    RoleLevel, ApprovalStatus,
    VoteStatus, VoteChoice
)


class ClanPermission(BaseModel):
    codename    = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    domain      = models.CharField(max_length=50)

    def __str__(self):
        return self.codename


class Role(BaseModel):
    clan            = models.ForeignKey(
                        Clan,
                        on_delete=models.PROTECT,
                        related_name='roles')
    name            = models.CharField(max_length=100)
    hierarchy_level = models.IntegerField(
                        choices=RoleLevel.CHOICES,
                        default=RoleLevel.MEMBER)
    permissions     = models.ManyToManyField(
                        ClanPermission,
                        blank=True,
                        related_name='roles')
    is_system_role  = models.BooleanField(default=False)
    inherits = models.ManyToManyField("self", symmetrical=False, blank=True, related_name="inherited_by")
    description     = models.TextField(blank=True)

    class Meta:
        unique_together = [('clan', 'name')]
        ordering = ['-hierarchy_level']

    def __str__(self):
        return f"{self.name} ({self.clan.name})"

    def delete(self, *args, **kwargs):
        if self.is_system_role:
            raise ValueError(
                f"System role '{self.name}' cannot be deleted."
            )
        super().delete(*args, **kwargs)


class MemberRole(BaseModel):
    member      = models.ForeignKey(
                    Member,
                    on_delete=models.PROTECT,
                    related_name='clan_roles')
    role        = models.ForeignKey(
                    Role,
                    on_delete=models.PROTECT,
                    related_name='assignments')
    assigned_by = models.ForeignKey(
                    Member,
                    on_delete=models.PROTECT,
                    related_name='roles_assigned')
    expires_at  = models.DateTimeField(null=True, blank=True)
    is_active   = models.BooleanField(default=True)
    notes       = models.TextField(blank=True)

    class Meta:
        unique_together = [('member', 'role')]

    def __str__(self):
        return f"{self.member} → {self.role.name}"

    @property
    def is_expired(self):
        if not self.expires_at:
            return False
        from django.utils import timezone
        return timezone.now() > self.expires_at

class ApprovalRequest(BaseModel):
    clan              = models.ForeignKey(
                          Clan,
                          on_delete=models.PROTECT,
                          related_name='approval_requests')
    action_type       = models.CharField(max_length=100)
    description       = models.TextField()
    payload           = models.JSONField(default=dict)
    status            = models.CharField(
                          max_length=20,
                          choices=ApprovalStatus.CHOICES,
                          default=ApprovalStatus.PENDING)
    initiated_by      = models.ForeignKey(
                          Member,
                          on_delete=models.PROTECT,
                          related_name='initiated_approvals')
    required_roles    = models.ManyToManyField(
                          Role,
                          related_name='required_for_approvals')
    minimum_approvals = models.IntegerField(default=2)
    resolved_at       = models.DateTimeField(null=True, blank=True)
    expires_at        = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.action_type} [{self.status}]"

    @property
    def approval_count(self):
        return self.votes.filter(vote='approve').count()

    @property
    def rejection_count(self):
        return self.votes.filter(vote='reject').count()


class ApprovalVote(BaseModel):
    request  = models.ForeignKey(
                 ApprovalRequest,
                 on_delete=models.PROTECT,
                 related_name='votes')
    voter    = models.ForeignKey(
                 Member,
                 on_delete=models.PROTECT,
                 related_name='approval_votes')
    vote     = models.CharField(
                 max_length=10,
                 choices=[('approve','Approve'),('reject','Reject')])
    reason   = models.TextField(blank=True)
    voted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('request', 'voter')]

    def __str__(self):
        return f"{self.voter} → {self.vote}"


class Vote(BaseModel):
    clan           = models.ForeignKey(
                       Clan,
                       on_delete=models.PROTECT,
                       related_name='votes')
    topic          = models.CharField(max_length=255)
    description    = models.TextField()
    initiated_by   = models.ForeignKey(
                       Member,
                       on_delete=models.PROTECT,
                       related_name='initiated_votes')
    status         = models.CharField(
                       max_length=20,
                       choices=VoteStatus.CHOICES,
                       default=VoteStatus.OPEN)
    quorum_percent = models.IntegerField(default=51)
    elder_approval_required = models.BooleanField(default=True)
    opens_at       = models.DateTimeField()
    closes_at      = models.DateTimeField()

    def __str__(self):
        return f"{self.topic} [{self.status}]"

    @property
    def yes_count(self):
        return self.casts.filter(choice=VoteChoice.YES).count()

    @property
    def no_count(self):
        return self.casts.filter(choice=VoteChoice.NO).count()


class VoteCast(BaseModel):
    vote    = models.ForeignKey(
                Vote,
                on_delete=models.PROTECT,
                related_name='casts')
    member  = models.ForeignKey(
                Member,
                on_delete=models.PROTECT,
                related_name='votes_cast')
    choice  = models.CharField(
                max_length=10,
                choices=VoteChoice.CHOICES)
    weight  = models.DecimalField(
                max_digits=4,
                decimal_places=2,
                default=1.00)
    cast_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('vote', 'member')]

    def __str__(self):
        return f"{self.member} → {self.choice}"