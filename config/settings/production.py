import os
import dj_database_url
from .base import *

DEBUG = False
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'bubabi.onrender.com').split(',')

# VALIDATE DATABASE URL - PostgreSQL REQUIRED
if not os.environ.get('DATABASE_URL'):
    raise ValueError("❌ DATABASE_URL environment variable is REQUIRED in production")

DATABASES = {
    'default': dj_database_url.config(
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# Verify PostgreSQL
db_engine = DATABASES['default']['ENGINE']
if 'postgresql' not in db_engine and 'postgres' not in db_engine:
    raise ValueError(f"❌ Production MUST use PostgreSQL, got {db_engine}")

# Security Headers
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True

SECURE_CONTENT_SECURITY_POLICY = {
    'default-src': ("'self'",),
    'script-src': ("'self'", "'unsafe-inline'", "cdn.jsdelivr.net"),
    'style-src': ("'self'", "'unsafe-inline'", "cdn.jsdelivr.net"),
    'img-src': ("'self'", "https:", "data:"),
    'font-src': ("'self'",),
    'connect-src': ("'self'", "bubabi.onrender.com", "res.cloudinary.com"),
    'frame-ancestors': ("'none'",),
    'base-uri': ("'self'",),
    'form-action': ("'self'",),
}

SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

PERMISSIONS_POLICY = {
    'accelerometer': ('none',),
    'camera': ('none',),
    'geolocation': ('none',),
    'microphone': ('none',),
    'payment': ('none',),
    'usb': ('none',),
}

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
    },
    'root': {'handlers': ['console'], 'level': 'INFO'},
}

# Email (use env vars)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')

# Sentry (error tracking)
if os.environ.get('SENTRY_DSN'):
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    sentry_sdk.init(
        dsn=os.environ.get('SENTRY_DSN'),
        integrations=[DjangoIntegration()],
        traces_sample_rate=0.1,
        send_default_pii=False
    )
