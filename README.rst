==================
Spring Replay Site
==================

|python| |license| |django|

Website to upload, download, search and comment replays created by games
running on the SpringRTS engine (http://springrts.com).

Runs on Django 3 and Python 3 (https://www.djangoproject.com/).

Development is done using Django 3.0 and Python 3.8. It may or may not run with other versions.
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
- requests: http://docs.python-requests.org/en/master/ (apt: python-requests)
- Pillow: https://pypi.python.org/pypi/Pillow/ (dev-python/pillow, pip install Pillow, enable JPEG, ZLIB and freetype support)
- DB-support: dev-python/mysql-python / python-mysqldb / sqlite/postgres/etc
- django-xmlrpc: https://github.com/Fantomas42/django-xmlrpc/
- python-magic: http://pypi.python.org/pypi/python-magic/ (version is around 0.4 - do NOT use python-magic-5.xx)
- timezone defs: dev-python/pytz | python-tz
- django-eztables: https://github.com/noirbizarre/django-eztables/
- django-utils: https://github.com/dansan/django-utils/
- django_extensions
- jsonrpc

Installation
============

Python 3.8
^^^^^^^^^^
To install Python 3.8 in a Debian system that does not yet have it in the distro repos::

    $ cat /etc/apt/sources.list >> /etc/apt/sources.list.d/testing.list
    $ vi  /etc/apt/sources.list.d/testing.list-> replace "deb" with "deb-src"
    # apt-get update
    $ apt-get build-dep python3.8 / 3.5 / 3.6 / 3.7
    # rm /etc/apt/sources.list.d/testing.list
    $ wget https://www.python.org/ftp/python/3.8.1/Python-3.8.1.tgz
    $ tar xzf Python-3.8.1.tgz
    $ cd Python-3.8.1
    # append "--prefix=~/python3.8" to the ./configure command...
    # if you don't have system wide write permissions:
    $ ./configure --enable-optimizations --with-ensurepip=install
    $ nice make -j $(nproc)
    # zzz ~1h...
    $ make altinstall  # maybe use "sudo"

Virtualenv
^^^^^^^^^^
Then create a virtualenv to install the projects dependencies into::

    $ sudo aptitude install libzmq-dev libfreetype6-dev
    $ python3.8 -m venv srs
    $ . srs/bin/activate
    (srs) $ pip install -U pip

Python packages
^^^^^^^^^^^^^^^
Some software has to be installed from git:

- install django-eztables from https://github.com/dansan/django-eztables.git
- install django-utils from https://github.com/dansan/django-utils.git
- install django.js from https://github.com/veeloinc/django.js.git

Install from git::

    (srs) $ pip install git+git://github.com/dansan/django-eztables.git
    (srs) $ pip install git+git://github.com/dansan/django-utils.git
    (srs) $ pip install git+git://github.com/veeloinc/django.js.git

Now install further requirements::

    (srs) $ pip install -U -r requirements.txt

The ``django-eztables`` packages ``views.py`` needs to be patched using ``eztables-GET.patch``::

    (srs) $ vi /home/replays/venv/lib/python3.8/site-packages/eztables/views.py
    #patch the content of eztables-GET.patch

To setup the SQL database copy ``local_settings_.py`` to ``local_settings.py``, and overwrite default settings there (at least ``DATABASES`` and ``ADMINS``).

The install the database schemas and static files::

    (srs) $ ./manage.py makemigrations background_task
    (srs) $ ./manage.py migrate
    (srs) $ crontab -e

Add the following to your crontab::

    MAILTO="me@myemail.com"

    0 0 * * *  ionice -c3 nice -n 19 .../virtenvs/srs/bin/python3.8 .../spring-replay-site/manage.py process_tasks --duration 86100 --log-std
    30 1 * * * ionice -c3 nice -n 19 .../virtenv/bin/python3.8 /var/www/servers/replays.springrts.com/spring-replay-site/manage.py delete_old_replay_files

Finally go to the /admin/ page and create a ``Lobbyauth->User_profile`` for your admin user.


.. |license| image:: https://img.shields.io/badge/License-GPLv3-orange.svg
    :alt: GNU General Public License 3
    :target: https://www.gnu.org/licenses/gpl-3.0
.. |python| image:: https://img.shields.io/badge/python-3.8-blue.svg
    :alt: Python 3.8
    :target: https://www.python.org/downloads/release/python-381/
.. |django| image:: https://www.djangoproject.com/m/img/badges/djangosite80x15.gif
    :alt: A Django site
    :target: http://www.djangoproject.com/