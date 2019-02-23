#!/usr/bin/env python

# This file is part of the "spring relay site / srs" program. It is published
# under the GPLv3.
#
# Copyright (C) 2019 Daniel Troeder (daniel #at# admin-box #dot# com)
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Django manage.py command to delete 3y old replay files.
"""

import os
import time
import logging
import datetime
from django.utils import timezone
from django.core.management.base import BaseCommand
from srs.models import Replay


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def handle(self, *args, **options):
        tz = timezone.get_current_timezone()
        now = datetime.datetime.now(tz)
        start_date = datetime.datetime(1970, 1, 1, tzinfo=tz)
        end_date = now - datetime.timedelta(days=3*365)
        replays = Replay.objects.filter(unixTime__range=(start_date, end_date)).order_by('pk')
        total = replays.count()
        current = 0  # not using enumerate() to prevent fetching complete SQL result set
        logger.info('Going to delete %d replay files...', total)
        for replay in replays:
            current += 1
            path = os.path.join(replay.path, replay.filename)
            logger.info('Deleting %d/%d: %s %s %s %s (%r)...', current, total, replay.pk,
                        replay.unixTime.strftime('%Y-%m-%d %H:%M:%S'), replay.gameID, replay.title, path)
            try:
                os.remove(path)
            except OSError as exc:
                logger.error('Error deleting %r: %s', path, exc)
            else:
                replay.path = ''
                replay.filename = ''
                replay.save()
            time.sleep(0.5)  # be gentile to the lobby servers I/O
        logger.info('Finished deleting old replays.')
