# This file is part of the "spring relay site / srs" program. It is published
# under the GPLv3.
#
# Copyright (C) 2016-2020 Daniel Troeder (daniel #at# admin-box #dot# com)
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import logging

from .models import Map, Replay, SldbMatchSkillsCache
from .sldb import SLDBError, get_sldb_match_skills
from .springmaps import SpringMaps

logger = logging.getLogger(__name__)


def fix_missing_winner(replay):
    logger.info("fix_missing_winner(%s)", replay)
    SldbMatchSkillsCache.objects.filter(gameID=replay.gameID).delete()
    try:
        match_skills = get_sldb_match_skills([replay.gameID])
        if match_skills:
            match_skills = match_skills[0]
    except SLDBError as exc:
        logger.error("get_sldb_match_skills(%s): %s", [replay.gameID], exc)
        return

    if match_skills and match_skills["status"] == 0:
        match_skills_by_pa = dict()
        for player in match_skills["players"]:
            match_skills_by_pa[player["account"]] = [s[0] for s in player["skills"][:2]]
    else:
        logger.error("No TS data for match from SLDB available, no fix possible.")
        return
    for at in replay.allyteam_set.all():
        pas = [team.teamleader.account for team in at.team_set.all()]
        try:
            at_sum_old = sum(match_skills_by_pa[pa][0] for pa in pas)
            at_sum_new = sum(match_skills_by_pa[pa][1] for pa in pas)
        except KeyError:
            logger.error("Player ID inconsistency between SLDB and replay data detected. Ignoring result.")
            logger.error(
                "match_skills=%r match_skills_by_pa=%r",
                match_skills,
                match_skills_by_pa,
            )
            return

        logger.info("Allyteam %s has rating change %r -> %r.", at, at_sum_old, at_sum_new)
        if at_sum_new > at_sum_old:
            logger.info("Allyteam %s has won.", at)
            at.winner = True
            at.save()
        else:
            logger.info("Allyteam %s has lost.", at)
            at.winner = False
            at.save()


def fix_missing_winner_all_replays():
    for replay in Replay.objects.exclude(allyteam__winner=True).filter(rated=True):
        fix_missing_winner(replay)


def fix_missing_map(replay):
    logger.info("fix_missing_map(%s)", replay)
    sm = SpringMaps(replay.map_info.name)
    sm.fetch_info()
    if not sm.map_info:
        logger.error("Could not retrieve map information.")
        return
    sm.fetch_img()
    sm.make_home_thumb()
    replay.map_info.metadata2 = sm.map_info[0]
    replay.map_info.save()


def update_map_info_urls(map_info: Map):
    sm = SpringMaps(map_info.name)
    sm.fetch_info()
    if sm.map_info and map_info.metadata2:
        if "mapimages" in sm.map_info[0]:
            map_info.metadata2["mapimages"] = sm.map_info[0]["mapimages"]
        if "mirrors" in sm.map_info[0]:
            map_info.metadata2["mirrors"] = sm.map_info[0]["mirrors"]
        map_info.save(update_fields=("metadata2",))
    else:
        logger.error("Error fetching map info for %r (%r).", map_info.name, map_info.pk)
