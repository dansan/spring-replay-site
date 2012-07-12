# edit and rename to local_settings.py

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
CACHE_MIDDLEWARE_SECONDS=600
CACHE_MIDDLEWARE_KEY_PREFIX=''

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}
