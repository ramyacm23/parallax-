import sys
from pathlib import Path
from decouple import config
BASE_DIR = Path(__file__).resolve().parent.parent
LOCAL_DEV_COMMANDS = {'runserver', 'test', 'check'}
IS_LOCAL_DEV_COMMAND = any(command in sys.argv for command in LOCAL_DEV_COMMANDS)
def get_debug_flag():
    raw_value = config('DEBUG', default='True')
    normalized = str(raw_value).strip().lower()
    if normalized in {'1', 'true', 'yes', 'on'}:
        return True
    if normalized in {'0', 'false', 'no', 'off', 'release', 'prod', 'production'}:
        return False
    return True
def get_staticfiles_storage():
    manifest_path = BASE_DIR / 'staticfiles' / 'staticfiles.json'
    if DEBUG or not manifest_path.exists():
        return 'django.contrib.staticfiles.storage.StaticFilesStorage'
    return 'whitenoise.storage.CompressedManifestStaticFilesStorage'
SECRET_KEY = config('DJANGO_SECRET_KEY', default='dev-insecure-change-in-production')
DEBUG = get_debug_flag()
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',')
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'parallax',
    'core',
]
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
ROOT_URLCONF = 'parallax.urls'
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]
SITE_ID = 1
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]
LOGIN_REDIRECT_URL = '/dashboard/'
ACCOUNT_EMAIL_VERIFICATION = 'none'
ACCOUNT_LOGOUT_ON_GET = True
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'APP': {
            'client_id': config('GOOGLE_CLIENT_ID', default='PLACEHOLDER_CLIENT_ID'),
            'secret': config('GOOGLE_CLIENT_SECRET', default='PLACEHOLDER_CLIENT_SECRET'),
            'key': '',
        },
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
    }
}
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='placeholder.parallax@gmail.com')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='PLACEHOLDER_APP_PASSWORD')
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
REQUIRE_INVOICE_VERIFICATION = config('REQUIRE_INVOICE_VERIFICATION', default=False, cast=bool)

# External event hub the leader is sent to for team creation and payment (step 3).
EVENT_HUB_URL = config('EVENT_HUB_URL', default='https://eventhub.example.com/parallax')
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = get_staticfiles_storage()
WHITENOISE_USE_FINDERS = DEBUG or IS_LOCAL_DEV_COMMAND
WHITENOISE_AUTOREFRESH = DEBUG or IS_LOCAL_DEV_COMMAND
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
