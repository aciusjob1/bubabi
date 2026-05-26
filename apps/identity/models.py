import uuid
from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin
)
from apps.core.models import BaseModel
from .constants import MemberStatus, Gender


class Person(BaseModel):
    full_name  = models.CharField(max_length=255)
    gender     = models.CharField(max_length=10, choices=Gender.CHOICES)
    birth_date = models.DateField()
    death_date = models.DateField(null=True, blank=True)
    biography  = models.TextField(blank=True)
    profile_image = models.ImageField(
        upload_to='profiles/', 
        null=True, 
        blank=True,
        help_text="Profile photo"
    )
    
    class Meta:
        ordering = ['full_name']

    def __str__(self):
        return self.full_name

    @property
    def is_deceased(self):
        return self.death_date is not None

    @property
    def age(self):
        from datetime import date
        end = self.death_date or date.today()
        return (end - self.birth_date).days // 365

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.death_date and self.death_date < self.birth_date:
            raise ValidationError("Death date cannot be before birth date.")


class Clan(BaseModel):
    contact_email = models.EmailField(max_length=255, blank=True, default="")
    contact_phone = models.CharField(max_length=50, blank=True, default="")
    payment_methods = models.TextField(default="{}", blank=True, null=True)
    # ── Identity ────────────────────────
    name = models.CharField(max_length=255, unique=True)
    code = models.CharField(max_length=10, blank=True, help_text="Short acronym")
    motto = models.CharField(max_length=255, blank=True, help_text="Clan motto or slogan")
    description = models.TextField(blank=True, help_text="Brief history or description")

    # ── Branding ────────────────────────
    logo = models.ImageField(upload_to='clan_logos/', blank=True, null=True)
    banner_image = models.ImageField(upload_to='clan_banners/', blank=True, null=True)
    primary_color = models.CharField(max_length=7, default='#10b981')
    accent_color = models.CharField(max_length=7, default='#6366f1')
    sidebar_color = models.CharField(max_length=20, default='#3d1a1a')
    blur_intensity = models.CharField(max_length=10, default='16px')

    # ── Financial defaults ──────────────
    currency = models.CharField(max_length=3, default='TZS')
    default_contribution = models.DecimalField(max_digits=12, decimal_places=2, default=50000)
    late_fine_amount = models.DecimalField(max_digits=12, decimal_places=2, default=10000)
    max_loan_amount = models.DecimalField(max_digits=12, decimal_places=2, default=500000)

    # ── Preferences ─────────────────────
    timezone = models.CharField(max_length=50, default='Africa/Dar_es_Salaam')
    default_language = models.CharField(max_length=10, choices=[('en', 'English'), ('sw', 'Kiswahili')], default='sw')
    is_public = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Clan'
        verbose_name_plural = 'Clans'

    def __str__(self):
        return self.name


class MemberManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user  = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('status', MemberStatus.ACTIVE)
        return self.create_user(email, password, **extra_fields)


class Member(AbstractBaseUser, PermissionsMixin, BaseModel):
    person     = models.ForeignKey(Person, on_delete=models.PROTECT, related_name='memberships', null=True, blank=True)
    clan       = models.ForeignKey(Clan, on_delete=models.PROTECT, related_name='members', null=True, blank=True)
    status     = models.CharField(max_length=20, choices=MemberStatus.CHOICES, default=MemberStatus.INVITED)
    email      = models.EmailField(unique=True)
    phone      = models.CharField(max_length=20, blank=True)
    joined_at  = models.DateTimeField(null=True, blank=True)
    invited_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='invitees')
    invited_at = models.DateTimeField(auto_now_add=True)
    is_staff   = models.BooleanField(default=False)
    is_active  = models.BooleanField(default=True)
    is_blocked = models.BooleanField(default=False, help_text="Blocked from accessing the system")
    has_accepted_terms = models.BooleanField
    has_accepted_terms = models.BooleanField(default=False, help_text="Has accepted terms of service")
    has_accepted_legal = models.BooleanField(default=False, help_text="Has accepted legal terms")
    accepted_terms_at = models.DateTimeField(null=True, blank=True)
    accepted_terms_ip = models.GenericIPAddressField(null=True, blank=True)
    accepted_terms_version = models.CharField(max_length=10, default="v1")
    blocked_at = models.DateTimeField(null=True, blank=True)
    blocked_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='blocked_members')
    block_reason = models.TextField(blank=True)

    USERNAME_FIELD  = 'email'
    REQUIRED_FIELDS = []

    objects = MemberManager()

    class Meta:
        unique_together = [('person', 'clan')]

    def __str__(self):
        if self.person:
            return f"{self.person.full_name} ({self.email})"
        return self.email

    @property
    def is_elder(self):
        """A member is an elder if they have an active Elder role OR are superuser."""
        if self.is_superuser:
            return True
        return self.clan_roles.filter(is_active=True, role__name='Elder').exists()
    @property
    def is_leader(self):
        if self.is_superuser:
            return True
        return self.clan_roles.filter(is_active=True, role__name='Leader').exists()

    @property
    def is_moderator(self):
        if self.is_superuser:
            return True
        return self.clan_roles.filter(is_active=True, role__name__in=['Moderator', 'Deputy Leader']).exists()

        return highest.role.hierarchy_level if highest else 0
    @property
    def max_role_level(self):
        """Return highest hierarchy level from active roles."""
        if self.is_superuser:
            return 5
        highest = self.clan_roles.filter(is_active=True).select_related("role").order_by("-role__hierarchy_level").first()
        return highest.role.hierarchy_level if highest else 0

    def is_treasurer(self):
        if self.is_superuser:
            return True
        return self.clan_roles.filter(is_active=True, role__name='Treasurer').exists()

    @property
    def is_secretary(self):
        if self.is_superuser:
            return True
        return self.clan_roles.filter(is_active=True, role__name='Secretary').exists()

    @property
    def is_moderator(self):
        """Check if member has moderation privileges (elder level or above)."""
        from apps.governance.constants import RoleLevel
        if not hasattr(self, 'clan_roles'):
            return False
        return self.clan_roles.filter(
            is_active=True,
            role__hierarchy_level__gte=RoleLevel.ELDER
        ).exists()


class MemberStatusHistory(BaseModel):
    member      = models.ForeignKey(Member, on_delete=models.PROTECT, related_name='status_history')
    from_status = models.CharField(max_length=20)
    to_status   = models.CharField(max_length=20)
    changed_by  = models.ForeignKey(Member, on_delete=models.PROTECT, related_name='status_changes_made')
    reason      = models.TextField(blank=True)
    timestamp   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']


class Notification(BaseModel):
    TYPES = [
        ('contribution_due', 'Contribution Due'),
        ('contribution_late', 'Contribution Late'),
        ('fine_issued', 'Fine Issued'),
        ('loan_approved', 'Loan Approved'),
        ('loan_rejected', 'Loan Rejected'),
        ('loan_disbursed', 'Loan Disbursed'),
        ('vote_opened', 'Vote Opened'),
        ('vote_closing', 'Vote Closing Soon'),
        ('meeting_reminder', 'Meeting Reminder'),
        ('member_invited', 'Member Invited'),
        ('status_changed', 'Status Changed'),
        ('announcement', 'Announcement'),
        ('general', 'General'),
    ]
    recipient  = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='notifications')
    notif_type = models.CharField(max_length=30, choices=TYPES)
    title      = models.CharField(max_length=255)
    message    = models.TextField()
    is_read    = models.BooleanField(default=False)
    link       = models.CharField(max_length=255, blank=True)
    sent_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-sent_at']

    def __str__(self):
        return f"{self.recipient} — {self.title}"


class Announcement(BaseModel):
    CATEGORIES = [
        ('general', 'General'),
        ('urgent', 'Urgent'),
        ('financial', 'Financial'),
        ('event', 'Event'),
        ('governance', 'Governance'),
    ]
    clan       = models.ForeignKey(Clan, on_delete=models.PROTECT, related_name='announcements')
    author     = models.ForeignKey(Member, on_delete=models.PROTECT, related_name='announcements')
    title      = models.CharField(max_length=255)
    content    = models.TextField()
    category   = models.CharField(max_length=20, choices=CATEGORIES, default='general')
    is_pinned  = models.BooleanField(default=False)
    is_active  = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    hidden_by  = models.ManyToManyField(Member, blank=True, related_name='hidden_announcements')

    class Meta:
        ordering = ['-is_pinned', '-created_at']

    def __str__(self):
        return self.title


class AnnouncementComment(BaseModel):
    announcement = models.ForeignKey(Announcement, on_delete=models.CASCADE, related_name='comments')
    author       = models.ForeignKey(Member, on_delete=models.PROTECT, related_name='announcement_comments')
    content      = models.TextField()

    class Meta:
        ordering = ['created_at']


# ══════════════════════════════════════════════
# CLAN FEED - POSTS
# ══════════════════════════════════════════════

class Post(BaseModel):
    clan = models.ForeignKey(Clan, on_delete=models.PROTECT, related_name='posts')
    author = models.ForeignKey(Member, on_delete=models.PROTECT, related_name='posts')
    content = models.TextField()
    image = models.ImageField(upload_to='posts/', null=True, blank=True)
    video = models.FileField(upload_to='posts/videos/', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    edited_at = models.DateTimeField(null=True, blank=True)
    is_hidden_by_reports = models.BooleanField(default=False)
    report_count = models.PositiveIntegerField(default=0)
    REPORT_THRESHOLD = 3

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['clan', '-created_at']),
            models.Index(fields=['author', '-created_at']),
        ]

    def __str__(self):
        return f"{self.author} — {self.content[:50]}"

    @property
    def like_count(self):
        return self.reactions.filter(reaction='like').count()

    @property
    def love_count(self):
        return self.reactions.filter(reaction='love').count()

    @property
    def laugh_count(self):
        return self.reactions.filter(reaction='laugh').count()

    @property
    def wow_count(self):
        return self.reactions.filter(reaction='wow').count()

    @property
    def sad_count(self):
        return self.reactions.filter(reaction='sad').count()

    @property
    def support_count(self):
        return self.reactions.filter(reaction='support').count()

    @property
    def comment_count(self):
        return self.post_comments.count()


class PostReaction(BaseModel):
    REACTIONS = [
        ('like', '👍'),
        ('love', '❤️'),
        ('laugh', '😂'),
        ('wow', '😮'),
        ('sad', '😢'),
        ('support', '🙏'),
    ]
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='reactions')
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='post_reactions')
    reaction = models.CharField(max_length=10, choices=REACTIONS)

    class Meta:
        unique_together = [('post', 'member')]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.member} {self.get_reaction_display()} on post {self.post.id}"


class PostComment(BaseModel):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='post_comments')
    author = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='post_comments')
    content = models.TextField(max_length=500)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.author} on post {self.post.id}: {self.content[:30]}"


class PostReport(BaseModel):
    REPORT_REASONS = [
        ('inappropriate', 'Inappropriate Content'),
        ('harassment', 'Harassment'),
        ('spam', 'Spam'),
        ('misinformation', 'Misinformation'),
        ('violence', 'Violence'),
        ('hate_speech', 'Hate Speech'),
        ('other', 'Other'),
    ]
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='reports')
    reported_by = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='post_reports_filed')
    reason = models.CharField(max_length=50, choices=REPORT_REASONS)
    details = models.TextField(blank=True)
    is_resolved = models.BooleanField(default=False)
    resolved_by = models.ForeignKey(Member, on_delete=models.SET_NULL, null=True, blank=True, related_name='post_reports_resolved')
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_note = models.TextField(blank=True)

    class Meta:
        unique_together = [('post', 'reported_by')]
        ordering = ['-created_at']

    def __str__(self):
        return f"Report on post {self.post.id} by {self.reported_by} - {self.reason}"
class ClanDocument(BaseModel):
    """Official clan documents: constitution, bylaws, judicial rulings."""
    DOCUMENT_TYPES = [
        ('constitution', 'Constitution'),
        ('bylaws', 'Bylaws'),
        ('judicial_ruling', 'Judicial Ruling'),
        ('code_of_conduct', 'Code of Conduct'),
        ('policy', 'Policy Document'),
        ('minutes_archive', 'Minutes Archive'),
        ('other', 'Other'),
    ]
    
    clan = models.ForeignKey(Clan, on_delete=models.CASCADE, related_name='documents')
    title = models.CharField(max_length=255)
    document_type = models.CharField(max_length=30, choices=DOCUMENT_TYPES, default='other')
    description = models.TextField(blank=True)
    file = models.FileField(upload_to='clan_documents/%Y/%m/')
    version = models.CharField(max_length=20, default='1.0')
    is_active = models.BooleanField(default=True)
    is_public = models.BooleanField(default=True, help_text="Visible to all members")
    uploaded_by = models.ForeignKey(Member, on_delete=models.PROTECT, related_name='uploaded_documents')
    effective_date = models.DateField(null=True, blank=True)
    review_date = models.DateField(null=True, blank=True, help_text="Next review date")
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_document_type_display()}: {self.title}"


class JudicialCase(BaseModel):
    """Clan judicial cases and rulings."""
    CASE_STATUS = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('appealed', 'Appealed'),
        ('dismissed', 'Dismissed'),
    ]
    
    CASE_TYPES = [
        ('dispute', 'Member Dispute'),
        ('land', 'Land Matter'),
        ('inheritance', 'Inheritance'),
        ('marriage', 'Marriage/Family'),
        ('conduct', 'Code of Conduct Violation'),
        ('other', 'Other'),
    ]
    
    clan = models.ForeignKey(Clan, on_delete=models.CASCADE, related_name='judicial_cases')
    case_number = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=255)
    case_type = models.CharField(max_length=30, choices=CASE_TYPES, default='other')
    description = models.TextField()
    parties_involved = models.TextField(help_text="Names of all parties involved")
    status = models.CharField(max_length=20, choices=CASE_STATUS, default='pending')
    ruling = models.TextField(blank=True, help_text="Final ruling/decision")
    ruling_date = models.DateField(null=True, blank=True)
    presided_by = models.ForeignKey(Member, on_delete=models.PROTECT, related_name='presided_cases', null=True, blank=True)
    filed_by = models.ForeignKey(Member, on_delete=models.PROTECT, related_name='filed_cases')
    attachment = models.FileField(upload_to='judicial_cases/', null=True, blank=True)
    is_confidential = models.BooleanField(default=False, help_text="Only visible to elders and above")
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Case #{self.case_number}: {self.title}"

class LegalAcceptance(models.Model):
    """Immutable record of every legal acceptance."""
    user = models.ForeignKey('Member', on_delete=models.CASCADE, related_name='legal_acceptances')
    terms_version = models.CharField(max_length=20)
    privacy_version = models.CharField(max_length=20)
    accepted_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    signature_hash = models.CharField(max_length=256)
    certificate_hash = models.CharField(max_length=256, blank=True, null=True)
    audit_chain_hash = models.CharField(max_length=256, blank=True, null=True)
    crypto_signature = models.TextField(blank=True, null=True)
    blockchain_anchor = models.TextField(blank=True, null=True)
    risk_score = models.IntegerField(default=0)
    risk_level = models.CharField(max_length=20, default="LOW")

    class Meta:
        indexes = [models.Index(fields=['user', 'accepted_at'])]
        ordering = ['-accepted_at']

    def __str__(self):
        return f"{self.user.email} accepted v{self.terms_version} at {self.accepted_at}"
