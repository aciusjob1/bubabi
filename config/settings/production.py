from .base import *
import dj_database_url
import os

DEBUG = False
ALLOWED_HOSTS = ['*']

# PostgreSQL from Render
DATABASES = {
    'default': dj_database_url.config(
        default=os.environ.get('DATABASE_URL'),
        conn_max_age=600,
    )
}

# Security
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Static files


# Media
MEDIA_ROOT = os.path.join(BASE_DIR, 'mediafiles')
MEDIA_URL = '/media/'

# Cloudinary media storage
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': os.environ.get('CLOUDINARY_CLOUD_NAME', ''),
    'API_KEY': os.environ.get('CLOUDINARY_API_KEY', ''),
    'API_SECRET': os.environ.get('CLOUDINARY_API_SECRET', ''),
}
STORAGES = {
    "default": {
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Debug cloudinary config
import logging
logger = logging.getLogger(__name__)
_cloud = CLOUDINARY_STORAGE.get('CLOUD_NAME', 'MISSING')
_key = CLOUDINARY_STORAGE.get('API_KEY', 'MISSING')
logger.info(f"CLOUDINARY CONFIG - cloud:{_cloud} key:{_key}")
