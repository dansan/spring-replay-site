"""
WSGI config for spring-replay-site project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.9/howto/deployment/wsgi/
"""

import os
import sys
from os.path import realpath, dirname
from django.core.wsgi import get_wsgi_application

# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "srs.settings")
os.environ["DJANGO_SETTINGS_MODULE"] = "srs.settings"

sys.path.append("/var/www/servers/replays-test.springrts.com/virtenv/lib/python2.7/site-packages/")
sys.path.append(realpath(realpath(dirname(__file__))+"/.."))

application = get_wsgi_application()
