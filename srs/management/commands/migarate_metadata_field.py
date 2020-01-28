#!/usr/bin/env python

# This file is part of the "spring relay site / srs" program. It is published
# under the GPLv3.
#
# Copyright (C) 2020 Daniel Troeder (daniel #at# admin-box #dot# com)
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Django manage.py command to migrate Map.metadata to Map.metadata2.
"""

import logging
import time

from django.core.management.base import BaseCommand

from srs.models import Map

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def handle(self, *args, **options):
        maps = Map.objects.filter(metadata2=None).order_by("pk")
        total = maps.count()
        logger.info("Going to migrate %d metadata fields...", total)
        for current, a_map in enumerate(maps, start=1):
            logger.info("Migrating %d/%d: %r...", current, total, a_map)
            a_map.metadata2 = a_map.metadata
            a_map.save(update_fields=("metadata2",))
            time.sleep(0.2)  # be gentile to the lobby servers I/O
        logger.info("Finished migrating metadata fields.")
        logger.info(
            "Maps with empty 'metadata2' fields: %d",
            Map.objects.filter(metadata2=None).count(),
        )
