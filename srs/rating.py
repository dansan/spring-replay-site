# This file is part of the "spring relay site / srs" program. It is published
# under the GPLv3.
#
# Copyright (C) 2012 Daniel Troeder (daniel #at# admin-box #dot# com)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.contrib.admin.views.decorators import staff_member_required

from models import *
from common import all_page_infos

from skills import GameInfo, Match
from skills import Player as SkillsPlayer
from skills import Team as SkillsTeam
from skills.elo import EloCalculator, EloRating


import logging
logger = logging.getLogger(__package__)


@staff_member_required
def initial_elo_rating(request):
    c = all_page_infos(request)

    c["rating_changes"] = list()
    for game in Game.objects.all():
        gamereleases = [gr.name for gr in GameRelease.objects.filter(game=game)]
        for replay in Replay.objects.filter(gametype__in=gamereleases, tags__name="1v1").exclude(tags__name__in=["Bot", "SP"]).order_by("unixTime"):
            rating_change = rate_match(replay)
            c["rating_changes"].append((game, replay, rating_change))

    logger.debug("rating_changes = %s", c["rating_changes"])
    return render_to_response('initial_elo_rating.html', c, context_instance=RequestContext(request))


def rate_match(replay):
    if replay.notcomplete:
        logger.error("Replay %s is not complete, cannot compute.", replay.gameID)

    game = Game.objects.get(gamerelease__name=replay.gametype)

    allyteams = Allyteam.objects.filter(replay=replay)

    rating_changes = list()

    teams = list()
    winner = list()
    for at in allyteams:
        teams.append(PlayerAccount.objects.filter(player__team__allyteam=at))
        if at.winner: winner.append(1)
        else: winner.append(2)

    # create rating objects for PlayerAccounts without it
    for pa in PlayerAccount.objects.filter(player__replay=replay, player__spectator=False):
        try:
            pa.rating
        except:
            Rating.objects.create(playeraccount=pa, game=game)

    if allyteams.count() == 2 and len(teams) == 2:
        # calculate ELO only for 1v1
        elo_teams = [SkillsTeam([(pa, EloRating(pa.rating.elo, pa.rating.elo_k)) for pa in team]) for team in teams]
        match = Match(elo_teams, winner)
        logger.debug("match = %s", match)
        # use lowest k-factor
        k_factor = reduce(min, [pa.rating.elo_k for pa in PlayerAccount.objects.filter(player__replay=replay, player__spectator=False)])

        game_info = GameInfo()
        elo_calculator = EloCalculator(k_factor=k_factor)
        elo_ratings = elo_calculator.new_ratings(game_info, match)

        logger.debug("PlayerAccount = %s", PlayerAccount.objects.filter(player__replay=replay, player__spectator=False))
        for pa in PlayerAccount.objects.filter(player__replay=replay, player__spectator=False):
            pa.rating.set_elo(elo_ratings.rating_by_id(pa))
            rating_changes.append((pa, elo_ratings.rating_by_id(pa)))

#TODO: glicko
#TODO: trueskill

    logger.debug("rating_changes = %s", rating_changes)
    return rating_changes
