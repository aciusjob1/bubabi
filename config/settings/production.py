import os
import dj_database_url
from .base import *

DEBUG = False

ALLOWED_HOSTS = [
    'bubabi.onrender.com',
    'localhost',
    '127.0.0.1',
]

# Database configuration targeting Render's PostgreSQL database
# Use SQLite for free hosting (Fly.io, etc.)
import os

# Database - auto-detect environment
if os.environ.get('RENDER', False) or os.environ.get('DATABASE_URL'):
    # Render.com or any PostgreSQL hosting
    DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db' / 'clan_prod.sqlite3',
    }
}
else:
    # Free hosting (Fly.io, local, etc.) - use SQLite
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db' / 'clan_prod.sqlite3',
        }
    }

# Keep old PostgreSQL config commented for reference
# DATABASES_OLD = {
    'default': dj_database_url.config(
        default=os.environ.get('DATABASE_URL'),
        conn_max_age=600
    )
}

# Production Storage Split Setup
# Cloudinary handles your persistent media uploads; WhiteNoise handles native CSS/JS assets
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'
STORAGES = {
    "default": {
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}
