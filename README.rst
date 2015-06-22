==================
Spring Replay Site
==================

Website to upload, download, search and comment replays created by games
running on the SpringRTS engine (http://springrts.com).

Runs on Django / Python (https://www.djangoproject.com/).

Development is done using Django 1.6 and Python 2.7. It may or may not run with other versions.
Latest source code can be found `on Github <https://github.com/dansan/spring-replay-site/>`_.

License
=======

This software is licensed as GPLv3, see COPYING.
jQuery, Bootstrap, Respond.js, Moment.js and bootstrap-daterangepicker are released under the terms of the MIT license.
html5shiv is dual licensed under the MIT or GPL Version 2 licenses.
selectize.js is licensed under the Apache License, Version 2.0.
Images under srs/static/img may have different copyright, some of which are not free in any way. To lazy to list all, do absolutely ask before using any of them!

Website
=======

The live site can be found at http://replays.springrts.com/ , a test site can be found at http://replays-test.springrts.com/
Associated forum thread on the SpringRTS developers forum: http://springrts.com/phpbb/viewtopic.php?f=71&t=28019

Dependencies
============

- jQuery UI: http://jqueryui.com/
- flowplayer: http://flowplayer.org/
- selectize.js: https://github.com/brianreavis/selectize.js/
- bootstrap-daterangepicker: https://github.com/dangrossman/bootstrap-daterangepicker/
- Moment.js: http://momentjs.com/

(regarding python: make a virtenv and use requirements.txt)

- Pillow 2.x: https://pypi.python.org/pypi/Pillow/ (dev-python/pillow, pip install Pillow, enable JPEG, ZLIB and freetype support)
- DB-support: dev-python/mysql-python / python-mysqldb / sqlite/postgres/etc
- suds: https://fedorahosted.org/suds/ (dev-python/suds / python-suds / etc)
    - I applied https://fedorahosted.org/suds/ticket/359/ (1/2 hunks succeeded -> fixed) 
- django-xmlrpc: https://github.com/Fantomas42/django-xmlrpc/
- python-magic: http://pypi.python.org/pypi/python-magic/
- timezone defs: dev-python/pytz | python-tz
- django-picklefield: https://pypi.python.org/pypi/django-picklefield/
- django-eztables: https://github.com/noirbizarre/django-eztables/
- django.js: https://github.com/noirbizarre/django.js/
- South: http://south.aeracode.org/
- django_extensions
- jsonrpc
- ipython
- watchdog
- Werkzeug

Installation
============

.. code-block:: bash

    $ virtualenv srs
    $ . srs/bin/activate
    (srs) $ pip install -r requirements.txt

- install django-eztables from https://github.com/dansan/django-eztables.git

.. code-block:: bash

    (srs) $ pip install git+git://github.com/dansan/django-eztables.git

- patch ``srs/lib/python2.7/site-packages/eztables/views.py`` using ``eztables-GET.patch``.

.. code-block:: bash

    (srs) $ cd srs
    (srs) $ patch -p0  < .../eztables-GET.patch

- install database schemas and static files

.. code-block:: bash

    (srs) $ ./manage.py migrate srs
    (srs) $ ./manage.py migrate lobbyauth
    (srs) $ ./manage.py collectstatic

- copy ``local_settings_.py`` to ``local_settings.py``, and overwrite default settings there.
