from django.db import models
from django.conf import settings

class UserSession(models.Model):
    """Track user sessions for security monitoring."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='tracked_sessions')
    session_key = models.CharField(max_length=40, unique=True, db_index=True)
    
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    expired_at = models.DateTimeField(null=True, blank=True)
    
    is_active = models.BooleanField(default=True, db_index=True)
    device_fingerprint = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    risk_score = models.IntegerField(default=0)
    country = models.CharField(max_length=100, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    logout_reason = models.CharField(max_length=50, blank=True, 
        choices=[
            ('user_logout', 'User Logout'),
            ('timeout', 'Session Timeout'),
            ('ip_change', 'IP Changed'),
            ('admin_kill', 'Admin Terminated'),
            ('browser_close', 'Browser Closed'),
        ])

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'User Session'
        verbose_name_plural = 'User Sessions'

    def __str__(self):
        return f"{self.user.email} — {self.ip_address or 'No IP'} — {'Active' if self.is_active else 'Ended'}"
