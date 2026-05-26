from pathlib import Path
from decouple import config
from django.contrib.messages import constants as message_constants

# ── Base directory ─────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ── Security ───────────────────────────────────────────────
SECRET_KEY = config('SECRET_KEY', default='dev-secret-key-change-in-production')
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = ['*']

# ── Installed apps ─────────────────────────────────────────
INSTALLED_APPS = [
    # 'axes',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third party
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'django_extensions',
    # Our apps
    'apps.core',
    'apps.identity',
    'apps.genealogy',
    'apps.governance',
    'apps.financials',
    'apps.events',
    'apps.audit',
]

# ── Middleware ─────────────────────────────────────────────
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'apps.identity.middleware.BlockedUserMiddleware',
    "apps.identity.middleware_terms.TermsAcceptanceMiddleware",
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'
WSGI_APPLICATION = 'config.wsgi.application'
AUTH_USER_MODEL = 'identity.Member'

# ── Templates ──────────────────────────────────────────────
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'apps.identity.context_processors.payment_methods',
                'apps.identity.context_processors.clan_settings',
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# ── Database (overridden per environment) ──────────────────
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db' / 'clan_dev.sqlite3',
        'OPTIONS': {'timeout': 20},
    }
}

# ── Auth ───────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ── Internationalisation ───────────────────────────────────
LANGUAGE_CODE = 'en'
TIME_ZONE = 'Africa/Dar_es_Salaam'  # Updated to TZ default
USE_I18N = True
USE_TZ = True

LANGUAGES = [
    ('en', 'English'),
    ('sw', 'Kiswahili'),
]

LOCALE_PATHS = [
    BASE_DIR / 'locale',
]

# ── Static & Media ─────────────────────────────────────────
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── REST Framework ─────────────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

# ── CORS ───────────────────────────────────────────────────
CORS_ALLOW_ALL_ORIGINS = True

# ── Login ──────────────────────────────────────────────────
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/dashboard/'

# ── CSRF ───────────────────────────────────────────────────
CSRF_TRUSTED_ORIGINS = [
    'http://127.0.0.1:8000',
    'http://127.0.0.1:8080',
    'http://127.0.0.1:8090',
    'http://localhost:8000',
    'http://0.0.0.0:8000',
]

# ── Messages ───────────────────────────────────────────────
MESSAGE_TAGS = {
    message_constants.ERROR: 'error',
    message_constants.SUCCESS: 'success',
    message_constants.WARNING: 'warning',
    message_constants.INFO: 'info',
}

# ── Clan System Defaults ──────────────────────────────────
# These are fallback defaults when clan-specific settings aren't configured
CLAN_CURRENCY = 'TSh'
CLAN_CURRENCY_CODE = 'TZS'
CLAN_DEFAULT_CONTRIBUTION = 50000
CLAN_DEFAULT_FINE = 10000
CLAN_MAX_LOAN_AMOUNT = 500000
CLAN_ELDER_AGE_THRESHOLD = 60
CLAN_LOAN_RESERVE_PERCENT = 20
CLAN_DEFAULT_TIMEZONE = 'Africa/Dar_es_Salaam'
CLAN_PRIMARY_COLOR = '#10b981'
CLAN_ACCENT_COLOR = '#6366f1'

# ── Africa's Talking SMS ──────────────────────────────────
AT_USERNAME = config('AT_USERNAME', default='sandbox')
AT_API_KEY = config('AT_API_KEY', default='')
AT_SENDER_ID = config('AT_SENDER_ID', default='BUBABI')

# ── Session ────────────────────────────────────────────────
SESSION_COOKIE_AGE = 1209600  # 2 weeks
SESSION_SAVE_EVERY_REQUEST = False

# ── File Upload ────────────────────────────────────────────
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10 MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10 MB

# ── Logging ────────────────────────────────────────────────
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}
# Custom authentication - email or phone login
AUTHENTICATION_BACKENDS = [
    'apps.identity.backends.EmailOrPhoneBackend',
    'django.contrib.auth.backends.ModelBackend',
]
