# copy to local_settings.py and overwrite settings there

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    ('Me', 'my@myself.I'),
)
MANAGERS = ADMINS

DATABASES = {
  'default': {
    'ENGINE'  : 'django.db.backends.sqlite3',
    'NAME'    : 'srs.db',
    'USER'    : '',
    'PASSWORD': '',
    'HOST'    : '',
    'PORT'    : '',
  }
}

CACHE_MIDDLEWARE_ALIAS='default'
CACHE_MIDDLEWARE_SECONDS=300
CACHE_MIDDLEWARE_KEY_PREFIX='test'

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
        'KEY_PREFIX': CACHE_MIDDLEWARE_KEY_PREFIX,
    }
}

DEFAULT_FROM_EMAIL = 'webmaster@replays.springrts.com'
SERVER_EMAIL       = 'webmaster@replays.springrts.com'

HALL_OF_FAME_MIN_MATCHES = 20

MEDIA_URL = 'http://replays.springrts.com/static/media/'

SLDB_URL         = ""
SLDB_ACCOUNT     = ""
SLDB_PASSWORD    = ""
SLDB_SKILL_ORDER = [("1", 0,), ("F", 1), ("T", 2), ("G", 3)]
SLDB_TIMEOUT     = 5
