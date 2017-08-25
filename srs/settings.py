# -*- coding: utf-8 -*-
from django.conf import global_settings
from os.path import realpath, dirname, abspath, join as path_join

SRS_FILE_ROOT = dirname(abspath(__file__))
IMG_PATH = path_join(SRS_FILE_ROOT, "static/img")
MAPS_PATH = path_join(SRS_FILE_ROOT, "static/maps")
REPLAYS_PATH = path_join(SRS_FILE_ROOT, "static/replays")
FONTS_PATH = path_join(SRS_FILE_ROOT, "static/fonts")
TS_HISTORY_GRAPHS_PATH = path_join(SRS_FILE_ROOT, "ts_graphs")
THUMBNAIL_SIZES = {"home": (150, 100), "replay": (340, 1000)}
LOGIN_URL = "/login/"
LOGOUT_URL = "/logout/"
ACCOUNT_ACTIVATION_DAYS = 4
REGISTRATION_OPEN = True
EMAIL_HOST = 'localhost'
DEFAULT_FROM_EMAIL = 'webmaster@replays.springrts.com'
LOGIN_REDIRECT_URL = '/'
DATE_FORMAT = 'd.m.Y'
DATETIME_FORMAT = DATE_FORMAT
SHORT_DATE_FORMAT = 'd.m.Y'
# SHORT_DATETIME_FORMAT = 'd.m.Y H:i:s (T)'
SHORT_DATETIME_FORMAT = SHORT_DATE_FORMAT
AUTHENTICATION_BACKENDS = ['lobbyauth.lobbybackend.LobbyBackend'] + list(global_settings.AUTHENTICATION_BACKENDS)
XMLRPC_METHODS = (('srs.upload.xmlrpc_upload', 'xmlrpc_upload'),)
INDEX_REPLAY_RANGE = 12
AUTH_PROFILE_MODULE = "lobbyauth.UserProfile"
DATA_UPLOAD_MAX_MEMORY_SIZE = 31457280

LOG_PATH = path_join(SRS_FILE_ROOT, 'log')
DEBUG_FORMAT = '%(asctime)s %(levelname)-8s %(module)s.%(funcName)s:%(lineno)d  %(message)s'
INFO_FORMAT = '%(asctime)s %(levelname)-8s %(message)s'
LOG_DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'

TIME_ZONE = 'Europe/Berlin'
LANGUAGE_CODE = 'en-us'
SITE_ID = 1
USE_I18N = True
USE_L10N = False
USE_TZ = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
MEDIA_ROOT = path_join(SRS_FILE_ROOT, "static/media")

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = path_join(SRS_FILE_ROOT, 'static')

STATIC_URL = '/static/'

MIDDLEWARE_CLASSES = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.http.ConditionalGetMiddleware',
    'django.middleware.cache.CacheMiddleware',
]

ROOT_URLCONF = 'srs.urls'

WSGI_APPLICATION = 'srs.wsgi.application'

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sitemaps',
    'srs',
    'infolog_upload',
    'lobbyauth',
    'django_comments',
    'django_xmlrpc',
    'djangojs',
    'eztables',
    'django_extensions',
    'jsonrpc',
    'background_task',
]

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [path_join(SRS_FILE_ROOT, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.request',
                'djangojs.context_processors.booleans',
            ],
            'builtins': ['djangojs.templatetags.js'],
        },
    },
]

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = "DENY"

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}


# import site specific settings, defaults first
from local_settings_ import *

# now overwrite default settings
try:
    from local_settings import *
except ImportError:
    print("ERROR: Please copy local_settings_.py to local_settings.py, and overwrite\n       default settings there.")
    exit(1)
