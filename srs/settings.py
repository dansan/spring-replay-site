# -*- coding: utf-8 -*-
from django.conf import global_settings
from os.path import realpath, dirname

SRS_FILE_ROOT = realpath(dirname(__file__))
IMG_PATH = SRS_FILE_ROOT+"/static/img/"
MAPS_PATH = SRS_FILE_ROOT+"/static/maps/"
REPLAYS_PATH = SRS_FILE_ROOT+"/static/replays/"
FONTS_PATH = SRS_FILE_ROOT+"/static/fonts/"
THUMBNAIL_SIZES = {"home": (150, 100), "replay": (340,1000)}
LOGIN_URL = "/login/"
LOGOUT_URL = "/logout/"
ACCOUNT_ACTIVATION_DAYS = 4
REGISTRATION_OPEN = True
EMAIL_HOST = 'localhost'
DEFAULT_FROM_EMAIL = 'webmaster@replays.springrts.com'
LOGIN_REDIRECT_URL = '/'
DATE_FORMAT = 'd.m.Y'
#DATETIME_FORMAT = 'd.m.Y H:i:s (T)'
DATETIME_FORMAT = DATE_FORMAT
SHORT_DATE_FORMAT = 'd.m.Y'
#SHORT_DATETIME_FORMAT = 'd.m.Y H:i:s (T)'
SHORT_DATETIME_FORMAT = SHORT_DATE_FORMAT
TEMPLATE_CONTEXT_PROCESSORS = global_settings.TEMPLATE_CONTEXT_PROCESSORS + ("django.core.context_processors.request", )
AUTHENTICATION_BACKENDS = ('lobbyauth.lobbybackend.LobbyBackend', ) + global_settings.AUTHENTICATION_BACKENDS
XMLRPC_METHODS = (('srs.upload.xmlrpc_upload', 'xmlrpc_upload'),)
INDEX_REPLAY_RANGE=12

LOG_PATH        = realpath(dirname(__file__))+'/log'
DEBUG_FORMAT = '%(asctime)s %(levelname)-8s %(module)s.%(funcName)s:%(lineno)d  %(message)s'
INFO_FORMAT  = '%(asctime)s %(levelname)-8s %(message)s'
LOG_DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Europe/Berlin'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = False

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = False

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = SRS_FILE_ROOT+"/static/media/"

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
#MEDIA_URL = 'http://127.0.0.1:8000/static/media/'
# --> local_settings.py

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = SRS_FILE_ROOT+'/static/'

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'z@=s%z(tp1faa%g1soppjrxs*kd2m!#avt_pc447#x(@=%m$+g'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.http.ConditionalGetMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.cache.CacheMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'srs.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'srs.wsgi.application'

TEMPLATE_DIRS = (
    # Don't forget to use absolute paths, not relative paths.
    SRS_FILE_ROOT+'/templates/'
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Uncomment the next line to enable the admin:
    'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
    'django.contrib.sitemaps',
    'srs',
    'lobbyauth',
    'django.contrib.comments',
    'django_xmlrpc',
    'djangojs',
    'eztables'
)

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

# import site specific settings
from local_settings_ import *
# overwrite default settings
from local_settings import *
