"""
Unified cost-effective notification service for BUBABI Clan System.
Priority: WhatsApp (free) > Email (free tier) > SMS (paid, last resort)
Providers: SMS (AT/Beem/BulkSMS), WhatsApp (Meta Cloud API), Email (Resend/Mailgun).
"""
import os
import json
import time
import hashlib
import logging
import requests
from datetime import datetime, timedelta
from decouple import config
from django.core.cache import cache

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# COST-SAVING SETTINGS
# ──────────────────────────────────────────────

# Priority order for notification channels (cheapest first)
CHANNEL_PRIORITY = ['whatsapp', 'email', 'sms']

# Minimum interval between same notification to same user (seconds)
DEDUP_WINDOW = {
    'contribution_reminder': 86400,    # 24 hours
    'fine_notification': 3600,         # 1 hour
    'loan_update': 3600,
    'meeting_reminder': 7200,          # 2 hours
    'announcement': 86400,             # 24 hours
    'general': 1800,                   # 30 minutes
}

# Batch SMS - send together every N seconds or when batch size reached
BATCH_SIZE = 10
BATCH_TIMEOUT = 60  # seconds


# ──────────────────────────────────────────────
# DEDUPLICATION HELPER
# ──────────────────────────────────────────────

def _dedup_key(member_id, notif_type, message):
    """Generate a unique deduplication key."""
    content = f"{member_id}:{notif_type}:{message[:50]}"
    return f"notif_dedup:{hashlib.md5(content.encode()).hexdigest()}"

def _should_send(member_id, notif_type, message):
    """Check if this notification should be sent (not a duplicate)."""
    key = _dedup_key(member_id, notif_type, message)
    window = DEDUP_WINDOW.get(notif_type, 1800)
    
    # Try Django cache first, fallback to in-memory
    try:
        if cache.get(key):
            logger.info(f"⏭️ Skipping duplicate: {notif_type} for member {member_id}")
            return False
        cache.set(key, True, window)
    except:
        pass
    return True


# ──────────────────────────────────────────────
# PHONE FORMATTING
# ──────────────────────────────────────────────

def format_phone(number):
    """Format phone to +255XXXXXXXXX."""
    if not number:
        return None
    num = str(number).strip().replace(' ', '').replace('-', '')
    if num.startswith('255'):
        return '+' + num
    elif num.startswith('0'):
        return '+255' + num[1:]
    elif num.startswith('+'):
        return num
    return '+255' + num


# ──────────────────────────────────────────────
# BASE SMS PROVIDER
# ──────────────────────────────────────────────

class BaseSMSProvider:
    def send(self, phone_numbers, message):
        raise NotImplementedError
    def test_connection(self):
        raise NotImplementedError
    @property
    def cost_per_sms(self):
        """Estimated cost per SMS in TZS."""
        return 0


# ──────────────────────────────────────────────
# AFRICA'S TALKING (~16-18 TSH/SMS)
# ──────────────────────────────────────────────

class AfricaTalkingProvider(BaseSMSProvider):
    cost_per_sms = 16

    def __init__(self):
        import africastalking
        self.username = config('AT_USERNAME', default='sandbox')
        self.api_key = config('AT_API_KEY', default='')
        self.sender_id = config('AT_SENDER_ID', default='BUBABI')
        africastalking.initialize(self.username, self.api_key)
        self.sms = africastalking.SMS
        self.is_sandbox = 'sandbox' in self.username.lower()

    def send(self, phone_numbers, message):
        formatted = [format_phone(n) for n in phone_numbers if format_phone(n)]
        if not formatted:
            return {'success': False, 'error': 'No valid numbers', 'cost': 0}
        if self.is_sandbox and 'Test' not in message:
            message = f"[Test] {message}"
        try:
            response = self.sms.send(message=message, recipients=formatted, sender_id=self.sender_id)
            return self._parse_response(response)
        except Exception as e:
            logger.error(f"AT SMS failed: {e}")
            return {'success': False, 'error': str(e), 'cost': 0}

    def _parse_response(self, response):
        recipients = response.get('SMSMessageData', {}).get('Recipients', [])
        success = sum(1 for r in recipients if r.get('status') == 'Success')
        total_cost = 0
        for r in recipients:
            cost_str = str(r.get('cost', '0')).replace('TZS', '').strip()
            try:
                total_cost += float(cost_str)
            except (ValueError, TypeError):
                total_cost += self.cost_per_sms if r.get('status') == 'Success' else 0
        return {'success': True, 'sent': success, 'total': len(recipients), 'cost': total_cost}

    def test_connection(self):
        try:
            import africastalking
            app = africastalking.Application
            resp = app.fetch_application_data()
            return {'success': True, 'balance': resp.get('UserData', {}).get('balance', 'N/A')}
        except Exception as e:
            return {'success': False, 'error': str(e)}


# ──────────────────────────────────────────────
# BEEM AFRICA (~10-12 TSH/SMS) - 30% CHEAPER
# ──────────────────────────────────────────────

class BeemAfricaProvider(BaseSMSProvider):
    cost_per_sms = 10

    def __init__(self):
        self.api_key = config('BEEM_API_KEY', default='')
        self.secret_key = config('BEEM_SECRET_KEY', default='')
        self.sender_id = config('BEEM_SENDER_ID', default='BUBABI')
        self.base_url = 'https://api.beem.africa/v1'

    def send(self, phone_numbers, message):
        formatted = [format_phone(n) for n in phone_numbers if format_phone(n)]
        if not formatted:
            return {'success': False, 'error': 'No valid numbers', 'cost': 0}
        if not self.api_key:
            return {'success': False, 'error': 'Beem API key not configured', 'cost': 0}
        headers = {
            'Authorization': f'Basic {self.api_key}',
            'Content-Type': 'application/json',
        }
        recipients = [{'recipient_id': str(i), 'dest_addr': num} for i, num in enumerate(formatted)]
        payload = {
            'source_addr': self.sender_id,
            'message': message,
            'recipients': recipients,
        }
        try:
            resp = requests.post(f'{self.base_url}/send', json=payload, headers=headers, timeout=15)
            data = resp.json()
            if data.get('code') == 100:
                sent_count = len(formatted)
                return {'success': True, 'sent': sent_count, 'total': sent_count, 'cost': sent_count * self.cost_per_sms, 'message_id': data.get('request_id')}
            return {'success': False, 'error': data.get('message', 'Unknown'), 'cost': 0}
        except Exception as e:
            logger.error(f"Beem SMS failed: {e}")
            return {'success': False, 'error': str(e), 'cost': 0}

    def test_connection(self):
        if not self.api_key:
            return {'success': False, 'error': 'API key not configured'}
        try:
            resp = requests.get(f'{self.base_url}/vendors/balance', headers={'Authorization': f'Basic {self.api_key}'}, timeout=10)
            data = resp.json()
            return {'success': True, 'balance': data.get('data', {}).get('credit_balance', 'N/A')}
        except Exception as e:
            return {'success': False, 'error': str(e)}


# ──────────────────────────────────────────────
# BULKSMS (~10-15 TSH/SMS)
# ──────────────────────────────────────────────

class BulkSMSProvider(BaseSMSProvider):
    cost_per_sms = 12

    def __init__(self):
        self.username = config('BULKSMS_USERNAME', default='')
        self.password = config('BULKSMS_PASSWORD', default='')
        self.sender_id = config('BULKSMS_SENDER_ID', default='BUBABI')

    def send(self, phone_numbers, message):
        formatted = [format_phone(n) for n in phone_numbers if format_phone(n)]
        if not formatted:
            return {'success': False, 'error': 'No valid numbers', 'cost': 0}
        if not self.username:
            return {'success': False, 'error': 'BulkSMS not configured', 'cost': 0}
        try:
            recipients = ','.join(formatted)
            url = 'https://api.bulksms.com/v1/messages'
            payload = {'to': recipients, 'body': message, 'from': self.sender_id}
            resp = requests.post(url, json=payload, auth=(self.username, self.password), timeout=15)
            sent_count = len(formatted) if resp.status_code == 200 else 0
            return {'success': resp.status_code == 200, 'sent': sent_count, 'total': len(formatted), 'cost': sent_count * self.cost_per_sms}
        except Exception as e:
            logger.error(f"BulkSMS failed: {e}")
            return {'success': False, 'error': str(e), 'cost': 0}

    def test_connection(self):
        if not self.username:
            return {'success': False, 'error': 'Not configured'}
        try:
            resp = requests.get('https://api.bulksms.com/v1/profile', auth=(self.username, self.password), timeout=10)
            return {'success': resp.status_code == 200}
        except Exception as e:
            return {'success': False, 'error': str(e)}


# ──────────────────────────────────────────────
# WHATSAPP (Meta Cloud API) - FREE within 24hr
# ──────────────────────────────────────────────

class WhatsAppProvider:
    def __init__(self):
        self.phone_number_id = config('WA_PHONE_NUMBER_ID', default='')
        self.access_token = config('WA_ACCESS_TOKEN', default='')
        self.api_version = config('WA_API_VERSION', default='v18.0')
        self.base_url = f'https://graph.facebook.com/{self.api_version}/{self.phone_number_id}'
        self.is_configured = bool(self.phone_number_id and self.access_token)

    def send_text(self, to_phone, message):
        if not self.is_configured:
            return {'success': False, 'error': 'WhatsApp not configured', 'cost': 0}
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json',
        }
        payload = {
            'messaging_product': 'whatsapp',
            'to': format_phone(to_phone),
            'type': 'text',
            'text': {'body': message},
        }
        try:
            resp = requests.post(f'{self.base_url}/messages', json=payload, headers=headers, timeout=15)
            data = resp.json()
            return {'success': resp.status_code == 200, 'message_id': data.get('messages', [{}])[0].get('id') if resp.status_code == 200 else None, 'cost': 0}
        except Exception as e:
            return {'success': False, 'error': str(e), 'cost': 0}

    def test_connection(self):
        if not self.is_configured:
            return {'success': False, 'error': 'Not configured'}
        try:
            headers = {'Authorization': f'Bearer {self.access_token}'}
            resp = requests.get(f'https://graph.facebook.com/{self.api_version}/{self.phone_number_id}', headers=headers, timeout=10)
            return {'success': resp.status_code == 200}
        except Exception as e:
            return {'success': False, 'error': str(e)}


# ──────────────────────────────────────────────
# EMAIL (Resend/Mailgun) - FREE TIER
# ──────────────────────────────────────────────

class EmailProvider:
    def __init__(self):
        self.provider = config('EMAIL_PROVIDER', default='resend').lower()
        self.from_email = config('FROM_EMAIL', default='noreply@bubabi.com')
        self.from_name = config('FROM_NAME', default='BUBABI Clan System')
        
        if self.provider == 'resend':
            self.api_key = config('RESEND_API_KEY', default='')
            self.base_url = 'https://api.resend.com'
        elif self.provider == 'mailgun':
            self.api_key = config('MAILGUN_API_KEY', default='')
            self.domain = config('MAILGUN_DOMAIN', default='')
            self.base_url = f'https://api.mailgun.net/v3/{self.domain}'
        
        self.is_configured = bool(self.api_key)

    def send(self, to_email, subject, html_body, text_body=''):
        if not self.is_configured:
            return {'success': False, 'error': 'Email not configured', 'cost': 0}
        if self.provider == 'resend':
            return self._send_resend(to_email, subject, html_body, text_body)
        elif self.provider == 'mailgun':
            return self._send_mailgun(to_email, subject, html_body, text_body)
        return {'success': False, 'error': 'Unknown provider', 'cost': 0}

    def _send_resend(self, to_email, subject, html_body, text_body):
        headers = {'Authorization': f'Bearer {self.api_key}', 'Content-Type': 'application/json'}
        payload = {'from': f'{self.from_name} <{self.from_email}>', 'to': [to_email] if isinstance(to_email, str) else to_email, 'subject': subject, 'html': html_body}
        if text_body:
            payload['text'] = text_body
        try:
            resp = requests.post(f'{self.base_url}/emails', json=payload, headers=headers, timeout=15)
            return {'success': resp.status_code == 200, 'message_id': resp.json().get('id'), 'cost': 0}
        except Exception as e:
            return {'success': False, 'error': str(e), 'cost': 0}

    def _send_mailgun(self, to_email, subject, html_body, text_body):
        try:
            data = {'from': f'{self.from_name} <{self.from_email}>', 'to': to_email, 'subject': subject, 'html': html_body}
            if text_body:
                data['text'] = text_body
            resp = requests.post(f'{self.base_url}/messages', auth=('api', self.api_key), data=data, timeout=15)
            return {'success': resp.status_code == 200, 'message_id': resp.json().get('id'), 'cost': 0}
        except Exception as e:
            return {'success': False, 'error': str(e), 'cost': 0}

    def test_connection(self):
        if not self.is_configured:
            return {'success': False, 'error': 'Not configured'}
        try:
            headers = {'Authorization': f'Bearer {self.api_key}'}
            resp = requests.get(f'{self.base_url}/emails', headers=headers, timeout=10) if self.provider == 'resend' else requests.get(f'{self.base_url}/events', auth=('api', self.api_key), timeout=10)
            return {'success': resp.status_code == 200}
        except Exception as e:
            return {'success': False, 'error': str(e)}


# ──────────────────────────────────────────────
# PROVIDER FACTORY
# ──────────────────────────────────────────────

def get_sms_provider():
    """Get the configured SMS provider."""
    provider_name = config('SMS_PROVIDER', default='africastalking').lower()
    providers = {
        'africastalking': AfricaTalkingProvider,
        'beem': BeemAfricaProvider,
        'bulksms': BulkSMSProvider,
    }
    provider_class = providers.get(provider_name, AfricaTalkingProvider)
    provider = provider_class()
    logger.info(f"📡 SMS Provider: {provider.__class__.__name__} (~{provider.cost_per_sms} TSH/SMS)")
    return provider


# ──────────────────────────────────────────────
# COST-EFFECTIVE NOTIFICATION ENGINE
# ──────────────────────────────────────────────

def send_smart_notification(member, title, message, notif_type='general', html_body=None, force_sms=False):
    """
    Smart notification that uses cheapest channel first.
    
    Priority:
    1. WhatsApp (FREE within 24hr window)
    2. Email (FREE tier - 3000/month Resend)
    3. SMS (PAID - last resort)
    
    With deduplication to avoid spam.
    """
    member_id = member.id if hasattr(member, 'id') else member
    
    # Deduplication check
    if not _should_send(member_id, notif_type, message):
        return {'sent': False, 'reason': 'duplicate', 'channel': None, 'cost': 0}
    
    phone = member.phone if hasattr(member, 'phone') else None
    email = member.email if hasattr(member, 'email') else None
    
    results = {'sent': False, 'channel': None, 'cost': 0}
    
    # 1. Try WhatsApp (FREE)
    if not force_sms and phone:
        wa = WhatsAppProvider()
        if wa.is_configured:
            result = wa.send_text(phone, f"*{title}*\n\n{message}")
            if result.get('success'):
                logger.info(f"✅ WhatsApp sent to {member}: 0 TSH")
                results = {'sent': True, 'channel': 'whatsapp', 'cost': 0}
                return results
    
    # 2. Try Email (FREE)
    if not force_sms and email:
        ep = EmailProvider()
        if ep.is_configured:
            html = html_body or f"<h2>{title}</h2><p>{message}</p>"
            result = ep.send(email, title, html, message)
            if result.get('success'):
                logger.info(f"✅ Email sent to {member}: 0 TSH")
                results = {'sent': True, 'channel': 'email', 'cost': 0}
                return results
    
    # 3. Fallback to SMS (PAID)
    if phone:
        provider = get_sms_provider()
        result = provider.send([phone], f"{title}: {message}")
        if result.get('success') and result.get('sent', 0) > 0:
            cost = result.get('cost', provider.cost_per_sms)
            logger.info(f"📤 SMS sent to {member}: {cost} TSH")
            results = {'sent': True, 'channel': 'sms', 'cost': cost, 'provider': provider.__class__.__name__}
            return results
    
    logger.warning(f"❌ All channels failed for {member}")
    results['reason'] = 'all_channels_failed'
    return results


def send_bulk_smart_notification(members, title, message, notif_type='general', force_sms=False):
    """
    Bulk notification with batching to reduce costs.
    Uses cheapest channels first.
    """
    total_cost = 0
    results = {'whatsapp': 0, 'email': 0, 'sms': 0, 'skipped': 0, 'failed': 0, 'total_cost': 0}
    
    # Collect recipients by channel
    wa_recipients = []
    email_recipients = []
    sms_recipients = []
    
    for member in members:
        if not _should_send(member.id, notif_type, message):
            results['skipped'] += 1
            continue
        
        phone = member.phone if hasattr(member, 'phone') else None
        email = member.email if hasattr(member, 'email') else None
        
        if not force_sms:
            wa = WhatsAppProvider()
            if wa.is_configured and phone:
                wa_recipients.append(member)
                continue
            ep = EmailProvider()
            if ep.is_configured and email:
                email_recipients.append(member)
                continue
        
        if phone:
            sms_recipients.append(member)
        else:
            results['failed'] += 1
    
    # Send WhatsApp (FREE)
    wa = WhatsAppProvider()
    for member in wa_recipients:
        r = wa.send_text(member.phone, f"*{title}*\n\n{message}")
        if r.get('success'):
            results['whatsapp'] += 1
        else:
            sms_recipients.append(member)  # Fallback to SMS
    
    # Send Email (FREE)
    ep = EmailProvider()
    for member in email_recipients:
        r = ep.send(member.email, title, f"<h2>{title}</h2><p>{message}</p>", message)
        if r.get('success'):
            results['email'] += 1
        elif member.phone:
            sms_recipients.append(member)
    
    # Send SMS in batches (PAID)
    if sms_recipients:
        provider = get_sms_provider()
        phones = [format_phone(m.phone) for m in sms_recipients if m.phone]
        for i in range(0, len(phones), BATCH_SIZE):
            batch = phones[i:i+BATCH_SIZE]
            r = provider.send(batch, f"{title}: {message[:140]}")
            if r.get('success'):
                sent = r.get('sent', 0)
                results['sms'] += sent
                total_cost += r.get('cost', 0)
    
    results['total_cost'] = total_cost
    cost_summary = f"FREE" if total_cost == 0 else f"TZS {total_cost:,.0f}"
    logger.info(f"📊 Bulk notification: WA={results['whatsapp']} Email={results['email']} SMS={results['sms']} Skipped={results['skipped']} Cost={cost_summary}")
    
    return results


# ──────────────────────────────────────────────
# BACKWARD COMPATIBILITY - SMSService
# ──────────────────────────────────────────────

class SMSService:
    """Backward-compatible SMS service using the configured provider."""
    
    @classmethod
    def send(cls, phone_numbers, message):
        provider = get_sms_provider()
        return provider.send(phone_numbers, message)
    
    @classmethod
    def send_bulk(cls, clan, message):
        from apps.identity.models import Member
        from apps.identity.constants import MemberStatus
        phones = list(Member.objects.filter(clan=clan, status=MemberStatus.ACTIVE).exclude(phone='').values_list('phone', flat=True))
        if phones:
            return cls.send([format_phone(p) for p in phones], message)
        return None
    
    @classmethod
    def test_connection(cls):
        provider = get_sms_provider()
        return provider.test_connection()
