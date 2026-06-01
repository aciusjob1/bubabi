"""Device fingerprinting for session security."""
import hashlib


def get_device_fingerprint(request):
    """Create unique device hash from browser characteristics."""
    raw = (
        request.META.get('HTTP_USER_AGENT', '') +
        request.META.get('HTTP_ACCEPT', '') +
        request.META.get('HTTP_ACCEPT_LANGUAGE', '') +
        request.META.get('HTTP_ACCEPT_ENCODING', '')
    )
    return hashlib.sha256(raw.encode()).hexdigest()[:64]


def get_client_ip(request):
    """Get real client IP behind proxies (Render/Cloudflare)."""
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    
    cf_ip = request.META.get('HTTP_CF_CONNECTING_IP')
    if cf_ip:
        return cf_ip
    
    return request.META.get('REMOTE_ADDR', '0.0.0.0')
