from .base import *

DEBUG = True

# TEMPLATES[0]['OPTIONS']['string_if_invalid'] = 'TEMPLATE_ERROR:%s'  # Disabled

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db' / 'clan_dev.sqlite3',
        'OPTIONS': {
            'timeout': 20,
        }
    }
}

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
STATICFILES_DIRS = [
    BASE_DIR / "static",
]
