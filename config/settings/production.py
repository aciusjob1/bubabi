import os
import dj_database_url
from .base import *

DEBUG = False

ALLOWED_HOSTS = [
    'bubabi.onrender.com',
    'localhost',
    '127.0.0.1',
]

# Database - auto-detect: PostgreSQL on Render, SQLite on Fly.io/local
if os.environ.get('RENDER') or os.environ.get('DATABASE_URL'):
    # Render.com PostgreSQL
    DATABASES = {
        'default': dj_database_url.config(
            default=os.environ.get('DATABASE_URL'),
            conn_max_age=600
        )
    }
else:
    # Fly.io / local - SQLite
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db' / 'clan_prod.sqlite3',
        }
    }

STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'
STORAGES = {
    "default": {
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

CSRF_TRUSTED_ORIGINS = [
    'https://bubabi.onrender.com',
    'https://bubabi.aciusjob1.workers.dev',
]

# Media files (Cloudinary)
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': os.environ.get('CLOUDINARY_CLOUD_NAME', ''),
    'API_KEY': os.environ.get('CLOUDINARY_API_KEY', ''),
    'API_SECRET': os.environ.get('CLOUDINARY_API_SECRET', ''),
}
MEDIA_ROOT = os.path.join(BASE_DIR, 'mediafiles')
MEDIA_URL = '/media/'

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
