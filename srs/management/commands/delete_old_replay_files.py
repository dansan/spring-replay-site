#!/usr/bin/env python

# This file is part of the "spring relay site / srs" program. It is published
# under the GPLv3.
#
# Copyright (C) 2019 Daniel Troeder (daniel #at# admin-box #dot# com)
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Django manage.py command to delete 2 month old replay files.
"""

import datetime
import logging
import os
import time

from django.core.management.base import BaseCommand
from django.utils import timezone

from srs.models import Replay
from srs.springmaps import SpringMaps

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def handle(self, *args, **options):
        tz = timezone.get_current_timezone()
        now = datetime.datetime.now(tz)
        start_date = datetime.datetime(1970, 1, 1, tzinfo=tz)
        end_date = now - datetime.timedelta(days=60)
        replays = (
            Replay.objects.exclude(path="", filename="").filter(unixTime__range=(start_date, end_date)).order_by("pk")
        )
        total = replays.count()
        logger.info("Going to delete %d replay files...", total)
        for current, replay in enumerate(replays, start=1):
            path = os.path.join(replay.path, replay.filename)
            logger.info(
                "Deleting %d/%d: %s %s %s %s (%r)...",
                current,
                total,
                replay.pk,
                replay.unixTime.strftime("%Y-%m-%d %H:%M:%S"),
                replay.gameID,
                replay.title,
                path,
            )
            try:
                os.remove(path)
            except OSError as exc:
                logger.error("Error deleting %r: %s", path, exc)
            replay.path = ""
            replay.filename = ""
            replay.save(update_fields=("filename", "path"))
            if replay.map_info:
                logger.info("Deleting replay map image...")
                sm = SpringMaps(replay.map_info.name)
                replay_image_filepath = sm.get_full_replay_image_filepath(replay.map_info.name, replay.gameID)
                try:
                    os.remove(replay_image_filepath)
                except OSError as exc:
                    logger.error("Error deleting %r: %s", path, exc)
            else:
                logger.info("Not deleting replay map image, as map_info attribute is not set (broken replay entry).")
            time.sleep(0.25)  # be gentile to the lobby servers I/O
        logger.info("Finished deleting old replays.")
