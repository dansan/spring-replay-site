# copy to local_settings.py and overwrite settings there

DEBUG = True

ADMINS = (
    ('Me', 'my@myself.I'),
)
MANAGERS = ADMINS

DATABASES = dict(
    default=dict(
        ENGINE='django.db.backends.sqlite3',
        NAME='srs.db',
        USER='',
        PASSWORD='',
        HOST='',
        PORT=''
    )
)

CONN_MAX_AGE = 10

# Make this unique, and don't share it with anybody.
SECRET_KEY = 's3cr3t'

CACHE_MIDDLEWARE_ALIAS = 'default'
CACHE_MIDDLEWARE_SECONDS = 300
CACHE_MIDDLEWARE_KEY_PREFIX = 'test'

CACHES = dict(
    default=dict(
        BACKEND='django.core.cache.backends.dummy.DummyCache',
        KEY_PREFIX=CACHE_MIDDLEWARE_KEY_PREFIX
    )
)

DEFAULT_FROM_EMAIL = 'webmaster@replays.springrts.com'
SERVER_EMAIL = 'webmaster@replays.springrts.com'

HALL_OF_FAME_MIN_MATCHES = 20

MEDIA_URL = 'http://replays.springrts.com/static/media/'

SLDB_URL = ""
SLDB_ACCOUNT = ""
SLDB_PASSWORD = ""
SLDB_SKILL_ORDER = [("1", 0,), ("F", 1), ("T", 2), ("G", 3), ("L", 4)]
SLDB_TIMEOUT = 3
SLDB_ALLOWED_IPS = ["78.46.100.156"]

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "replays.springrts.com", "replays-test.springrts.com",
                 "replays.admin-box.com", "replays-test.admin-box.com", "78.46.100.156",
                 "springrts.com", "78.46.100.157"]

PLATFORM_STATS_CREDENTIALS = ('username', 'password')
PLATFORM_STATS_URL = "http://127.0.0.1:8999/schema/"

# STATICFILES_DIRS = []

# logging.disable(logging.DEBUG)
