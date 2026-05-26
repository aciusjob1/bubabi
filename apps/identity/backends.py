from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from apps.identity.models import Member

User = get_user_model()

class EmailOrPhoneBackend(ModelBackend):
    """
    Authenticate using email OR phone number.
    Supports Tanzania phone formats: +255XXXXXXXXX, 0XXXXXXXXX, 255XXXXXXXXX
    """
    
    def authenticate(self, request, username=None, password=None, email=None, phone=None, **kwargs):
        if password is None:
            return None
        
        user = None
        
        # Try email first
        login_id = email or username
        if login_id:
            # Normalize email
            login_id = login_id.strip().lower()
            
            if '@' in login_id:
                # Email login
                try:
                    user = User.objects.get(email=login_id)
                except User.DoesNotExist:
                    pass
            else:
                # Phone login
                user = self._find_by_phone(login_id)
        
        # Explicit phone parameter
        if phone and not user:
            user = self._find_by_phone(phone)
        
        if user and user.check_password(password):
            return user
        
        return None
    
    def _find_by_phone(self, phone):
        """Find user by phone number in various formats."""
        phone = phone.strip().replace(' ', '').replace('-', '')
        
        # Try multiple formats
        formats = [phone]
        
        # Remove leading +
        if phone.startswith('+'):
            formats.append(phone[1:])
        else:
            formats.append('+' + phone)
        
        # Handle 0 prefix vs 255
        if phone.startswith('0'):
            formats.append('+255' + phone[1:])
            formats.append('255' + phone[1:])
        elif phone.startswith('255'):
            formats.append('0' + phone[3:])
            formats.append('+' + phone)
        elif phone.startswith('+255'):
            formats.append('0' + phone[4:])
            formats.append(phone[1:])
        
        for fmt in formats:
            try:
                return User.objects.get(phone=fmt)
            except User.DoesNotExist:
                continue
        
        return None
    
    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

