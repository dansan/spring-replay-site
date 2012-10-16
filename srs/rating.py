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
from django.views.decorators.cache import never_cache

from models import *
from common import all_page_infos

from skills import Match, Matches, RatingFactory
from skills import Player as SkillsPlayer
from skills import Team as SkillsTeam
from skills.elo import EloCalculator, EloRating, EloGameInfo
from skills.glicko import GlickoCalculator, GlickoRating, GlickoGameInfo
from skills.trueskill import TwoPlayerTrueSkillCalculator, TwoTeamTrueSkillCalculator, FactorGraphTrueSkillCalculator, GaussianRating, TrueSkillGameInfo

import csv, codecs, cStringIO, datetime

import logging
logger = logging.getLogger(__package__)

# from http://docs.python.org/library/csv.html
class UnicodeWriter:
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.queue = cStringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def writerow(self, row):
        self.writer.writerow([s.encode("utf-8") for s in row])
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)


@staff_member_required
@never_cache
def initial_rating(request):
    c = all_page_infos(request)

    try:
        csvfile = open(settings.LOG_PATH+'/initial_rating_%s.csv'%datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S"), 'wb')
        csvwriter = UnicodeWriter(csvfile, delimiter=',', quoting=csv.QUOTE_ALL)
        header = ["Game", "Replay", "Type"]
        for num in range(1, 3):
            header.extend(["Player %d"%num, "ELO", "Glicko", "TrueSkill"])
        for num in range(3, 17):
            header.extend(["Player %d"%num, "TrueSkill"])
        header.append("URL of replay")
        csvwriter.writerow(header)
    except Exception, e:
        logger.error("problem opening/writing csv file, exception: %s", e)

    c["rating_changes"] = list()
    for game in Game.objects.all():
        gamereleases = [gr.name for gr in GameRelease.objects.filter(game=game)]
        # copy QuerySet into list, so it doesn't change while running
        replays = list(Replay.objects.filter(gametype__in=gamereleases, tags__name__regex=r'^([0-9]v[0-9]|FFA|TeamFFA)$').exclude(tags__name__in=["Bot", "SP"]).distinct().order_by("unixTime"))
        logger.info("Game = %s, number of replays = %d", game, len(replays))
        replays_count = 1
        for replay in replays:
            try:
                rating_change = rate_match(replay, from_initial_rating=True)
            except Exception, e:
                logger.error("Problem rating Replay(%d, '%s'): %s", replay.pk, replay, e)
                replays_count += 1
                continue
            count = 1
            csv_row = [game.abbreviation, replay.unixTime.strftime("%Y-%m-%d %H:%M:%S"), replay.match_type()]
            for pa, elo_rating, glicko_rating, ts_rating in rating_change:
                csv_row.append(pa.get_names()[0])
                if count <= 2:
                    if elo_rating: csv_row.append("%.3f"%elo_rating.mean)
                    else: csv_row.append("")
                    if glicko_rating: csv_row.append("%.3f (%.1f)"%(glicko_rating.mean, glicko_rating.stdev))
                    else: csv_row.append("")
                if ts_rating: csv_row.append("%.3f (%.1f)"%(ts_rating.mean, ts_rating.stdev))
                else: csv_row.append("")
                count += 1

            for _ in range(16-len(rating_change)):
                rating_change.append((None, None, None, None))
                csv_row.extend(["", ""])
            c["rating_changes"].append((game, replay, rating_change))
            csv_row.append("http://replays.admin-box.com"+replay.get_absolute_url())
            csvwriter.writerow(csv_row)

            if replays_count%50 == 0:
                logger.info("... %d replays done", len(c["rating_changes"]))
            replays_count += 1

    logger.info("wrote csv to %s", csvfile.name)
    csvfile.close()

    # this is stupid, but I don't know how to do it better :)
    c["sixteen"] = range(1,17)
    return render_to_response('initial_rating.html', c, context_instance=RequestContext(request))


def rate_match(replay, from_initial_rating=False):
    if replay.notcomplete:
        raise Exception("Replay(%d) %s is not complete, cannot compute.", replay.pk, replay.gameID)

    if settings.INITIAL_RATING and not from_initial_rating:
        # queue match to be rated after initial_rating() has run
        RatingQueue.objects.create(replay=replay)
        raise Exception("initial_rating() is running, queued replay(%d) %s", replay.pk, replay.gameID)

    game = Game.objects.get(gamerelease__name=replay.gametype)

    allyteams = Allyteam.objects.filter(replay=replay)

    # do not allow bots
    if PlayerAccount.objects.filter(player__team__allyteam__in=allyteams, accountid=0).exists():
        raise Exception("Replay(%d) %s has a bot as player, not rating.", replay.pk, replay.gameID)

    rating_changes = list()

    teams = list()
    winner = list()
    for at in allyteams:
        ally_list = list()
        for team in Team.objects.filter(allyteam=at):
            ally_list.extend([player.account for player in Player.objects.filter(team=team)])
        teams.append(ally_list)
        if at.winner: winner.append(1)
        else: winner.append(2)

    # calculate ELO and Glicko only for 1v1 and no bots
    if allyteams.count() == 2 and PlayerAccount.objects.filter(player__team__allyteam__in=allyteams).exclude(accountid=0).count() == 2:
        RatingFactory.rating_class = EloRating
        elo_teams = [SkillsTeam([(pa, EloRating(pa.get_rating(game, replay.match_type_short()).elo, pa.get_rating(game, replay.match_type_short()).elo_k)) for pa in team]) for team in teams]
        elo_match = Match(elo_teams, winner)
        # use lowest k-factor
        k_factor = reduce(min, [pa.get_rating(game, replay.match_type_short()).elo_k for pa in PlayerAccount.objects.filter(player__replay=replay, player__spectator=False)])

        if not settings.ELO_ONLY:
            RatingFactory.rating_class = GlickoRating
            glicko_teams = [SkillsTeam([(pa, GlickoRating(pa.get_rating(game, replay.match_type_short()).glicko, pa.get_rating(game, replay.match_type_short()).glicko_rd)) for pa in team]) for team in teams]
            glicko_matches = Matches([Match(glicko_teams, winner)])

            RatingFactory.rating_class = GaussianRating
            ts_teams = [SkillsTeam([(pa, GaussianRating(pa.get_rating(game, replay.match_type_short()).trueskill_mu, pa.get_rating(game, replay.match_type_short()).trueskill_sigma)) for pa in team]) for team in teams]
            ts_match = Match(ts_teams, winner)

        elo_game_info = EloGameInfo(initial_mean=1500, beta=1500/6)
        glicko_game_info = GlickoGameInfo(initial_mean=1500, beta=1500/6)
        ts_game_info = TrueSkillGameInfo()

        elo_calculator = EloCalculator(k_factor=k_factor)
        elo_ratings = elo_calculator.new_ratings(elo_match, game_info=elo_game_info)
        if not settings.ELO_ONLY:
            glicko_calculator = GlickoCalculator()
            glicko_ratings = glicko_calculator.new_ratings(glicko_matches, game_info=glicko_game_info)
            #TODO: use glicko rating period
            ts_calculator = TwoPlayerTrueSkillCalculator()
            ts_ratings = ts_calculator.new_ratings(ts_match, game_info=ts_game_info)

        for pa in PlayerAccount.objects.filter(player__replay=replay, player__spectator=False):
            rating = pa.get_rating(game, replay.match_type_short())
            rating.set_elo(elo_ratings.rating_by_id(pa))
            if not settings.ELO_ONLY:
                rating.set_glicko(glicko_ratings.rating_by_id(pa))
                rating.set_trueskill(ts_ratings.rating_by_id(pa))
                rating_changes.append((pa, elo_ratings.rating_by_id(pa), glicko_ratings.rating_by_id(pa), ts_ratings.rating_by_id(pa)))
            else:
                rating_changes.append((pa, elo_ratings.rating_by_id(pa), None, None))
            rating_history = RatingHistory.objects.create(playeraccount=pa, match=replay, algo_change="C", game=game, match_type=replay.match_type_short())
            rating_history.set_elo(elo_ratings.rating_by_id(pa))
            if not settings.ELO_ONLY:
                rating_history.set_glicko(glicko_ratings.rating_by_id(pa))
                rating_history.set_trueskill(ts_ratings.rating_by_id(pa))
                rating_history.algo_change="A"
            else:
                rating_history.algo_change="E"
            rating_history.save()
    else:
        # use TrueSkill for Team and FFA matches
        RatingFactory.rating_class = GaussianRating
        ts_teams = [SkillsTeam([(pa, GaussianRating(pa.get_rating(game, replay.match_type_short()).trueskill_mu, pa.get_rating(game, replay.match_type_short()).trueskill_sigma)) for pa in team]) for team in teams]
        ts_match = Match(ts_teams, winner)

        game_info = TrueSkillGameInfo()
        if allyteams.count() == 2 and Team.objects.filter(allyteam=allyteams[0]).count() == Team.objects.filter(allyteam=allyteams[1]).count():
            ts_calculator = TwoTeamTrueSkillCalculator()
        else:
            # FactorGraphTrueSkillCalculator works for 1v1, Team and FFA games
            ts_calculator = FactorGraphTrueSkillCalculator()
        ts_ratings = ts_calculator.new_ratings(ts_match, game_info)

        for pa in PlayerAccount.objects.filter(player__replay=replay, player__spectator=False):
            pa.get_rating(game, replay.match_type_short()).set_trueskill(ts_ratings.rating_by_id(pa))
            rating_changes.append((pa, None, None, ts_ratings.rating_by_id(pa)))
            rating_history = RatingHistory.objects.create(playeraccount=pa, match=replay, algo_change="C", game=game, match_type=replay.match_type_short())
            rating_history.set_trueskill(ts_ratings.rating_by_id(pa))
            rating_history.algo_change="T"
            rating_history.save()

    logger.debug("rated replay(%d | %s): %s", replay.pk, replay.gameID, replay)
    return rating_changes
