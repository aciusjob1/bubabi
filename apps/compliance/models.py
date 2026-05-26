from django.db import models
from django.conf import settings

class Policy(models.Model):
    """Versioned compliance policy (Terms of Service, Privacy, etc.)"""
    key = models.CharField(max_length=100)  # "terms_of_service", "privacy_policy"
    version = models.CharField(max_length=20)  # "v1", "v2"
    is_active = models.BooleanField(default=True)
    title = models.CharField(max_length=255)
    content = models.TextField(blank=True)
    effective_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('key', 'version')
        ordering = ['-effective_at']
    
    def __str__(self):
        return f"{self.key} {self.version}"

class UserPolicyAcceptance(models.Model):
    """Immutable audit record of policy acceptance."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    policy = models.ForeignKey(Policy, on_delete=models.CASCADE)
    accepted_version = models.CharField(max_length=20)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    accepted_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'policy', 'accepted_version')
        ordering = ['-accepted_at']
