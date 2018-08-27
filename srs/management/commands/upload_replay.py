#!/usr/bin/env python

# This file is part of the "spring relay site / srs" program. It is published
# under the GPLv3.
#
# Copyright (C) 2018 Daniel Troeder (daniel #at# admin-box #dot# com)
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Django manage.py command to update one/some/all School object(s).
"""

import os.path
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from srs.models import SrsTiming
from srs.upload import parse_uploaded_file, timer as timer_


timer = timer_


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            'demofile',
            type=str,
            help='Path to demofile.'
        )

    def handle(self, *args, **options):
        global timer

        path = options['demofile']
        if not os.path.exists(path):
            raise CommandError('File {!r} does not exist.'.format(path))

        if not timer:
            timer = SrsTiming()
        timer.start("cmdline_upload()")
        UserModel = get_user_model()
        user = UserModel.objects.get(username='root')
        replay, msg = parse_uploaded_file(path, timer, None, None, 'Uploaded on cmdline.', user, False, True)
        self.stdout.write('Replay(id={}): {}'.format(replay.pk, msg))
        timer.stop("cmdline_upload()")
