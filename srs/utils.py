# This file is part of the "spring relay site / srs" program. It is published
# under the GPLv3.
#
# Copyright (C) 2016 Daniel Troeder (daniel #at# admin-box #dot# com)
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import logging
from srs.models import RatingHistory, Replay
from srs.springmaps import SpringMaps


logger = logging.getLogger("srs.utils")


def fix_missing_winner(replay):
    logger.info("fix_missing_winner(%s)", replay)
    match_rating_history = RatingHistory.objects.filter(match=replay, match_type=replay.match_type_short)
    if not match_rating_history.exists():
        logger.info("No TS data available, no fix possible.")
        return
    new_ratings = dict()
    old_ratings = dict()
    for at in replay.allyteam_set.all():
        new_at_ratings = match_rating_history.filter(playeraccount__in=[team.teamleader.account for team in at.team_set.all()])
        new_ratings[at] = sum([r.trueskill_mu for r in new_at_ratings])
        old_ratings[at] = 0
        old_ratings_li = list()
        for paid in at.team_set.values_list("player__account", flat=True):
            try:
                old_rating = RatingHistory.objects.filter(playeraccount__id=paid, game=replay.game_release.game,
                                                                 match_type=replay.match_type_short,
                                                                 match__unixTime__lt=replay.unixTime
                                                                 ).order_by("-match__unixTime")[0].trueskill_mu
            except IndexError:
                old_rating = 25
            old_ratings_li.append(old_rating)
            old_ratings[at] += old_rating
        logger.info("Allyteam %s has rating change %r -> %r." , at, old_ratings[at], new_ratings[at])
        if new_ratings[at] > old_ratings[at]:
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
    replay.map_info.metadata = sm.map_info[0]
    replay.map_info.save()
