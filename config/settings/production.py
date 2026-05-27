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
DATABASES = {
    'default': dj_database_url.config(
        default=os.environ.get('DATABASE_URL'),
        conn_max_age=600
    )
}

# Production Storage Split Setup
# Cloudinary handles your persistent media uploads; WhiteNoise handles native CSS/JS assets
STORAGES = {
    "default": {
        "BACKEND": "django_cloudinary_storage.storage.MediaCloudinaryStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.StaticFilesStorage",
    },
}
