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
        replays = list(Replay.objects.filter(gametype__in=gamereleases, tags__name__regex=r'^([0-9]v[0-9]|Duel|Team|FFA|TeamFFA)$').exclude(tags__name__in=["Bot", "SP"]).distinct().order_by("unixTime"))
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

def skill2num(skill):
    num = ""
    for i in range(len(skill)):
        if skill[i].isdigit() or skill[i] == ".":
            num += skill[i]
    return float(num)

def rate_match(replay, from_initial_rating=False, ba1v1tourney=False):
    if replay.notcomplete:
        raise Exception("Replay(%d) %s is not complete, cannot compute."%(replay.pk, replay.gameID))

    if settings.INITIAL_RATING and not from_initial_rating:
        # queue match to be rated after initial_rating() has run
        RatingQueue.objects.create(replay=replay)
        raise Exception("initial_rating() is running, queued replay(%d) %s"%(replay.pk, replay.gameID))

    game = replay.game_release().game
    allyteams = Allyteam.objects.filter(replay=replay)
    match_type_short = replay.match_type_short()
    match_type_short_b1t = replay.match_type_short(ba1v1tourney)

    # do not allow bots
    if replay.game_release().game.abbreviation in ["CD", "RD"] or PlayerAccount.objects.filter(player__replay=replay, accountid=0).exists():
        raise Exception("Replay(%d) %s has a bot, not rating."%(replay.pk, replay.gameID))

    rating_changes = list()

    players = Player.objects.filter(replay=replay, spectator=False)
    if players.exists() and players[0].skill != "":
        # use SLDBs values, don't calculate myself
        logger.debug("found skill values from SLDB")
        for pa, skill in [(player.account, skill2num(player.skill)) for player in players]:
            pa.get_rating(game, match_type_short).set_trueskill(GaussianRating(skill, 25))
            rating_changes.append((pa, None, None, GaussianRating(skill, 25)))
            rating_history = RatingHistory.objects.create(playeraccount=pa, match=replay, algo_change="T", game=game, match_type=match_type_short, trueskill_mu=skill)
    else:
        # calculate myself
        logger.debug("calculating skill myself")
        teams = [PlayerAccount.objects.filter(player__team__allyteam=at) for at in allyteams]

        # winner = 1
        # looser = 2
        # no winners -> all must be 1
        winner = [at.winner for at in allyteams]
        if not reduce(lambda x,y: x or y, winner):
            # no winners
            winner = [1 for _ in winner]
        else:
            winner = [int(not w)+1 for w in winner]

        pas_in_match = PlayerAccount.objects.filter(player__replay=replay, player__spectator=False)

        # calculate ELO and Glicko only for 1v1 and no bots
        if allyteams.count() == 2 and PlayerAccount.objects.filter(player__team__allyteam__in=allyteams).exclude(accountid=0).count() == 2:
            RatingFactory.rating_class = EloRating
            elo_teams = [SkillsTeam([(pa, EloRating(pa.get_rating(game, match_type_short_b1t).elo, pa.get_rating(game, match_type_short_b1t).elo_k)) for pa in team]) for team in teams]
            elo_match = Match(elo_teams, winner)
            # use lowest k-factor
            k_factor = reduce(min, [pa.get_rating(game, match_type_short_b1t).elo_k for pa in pas_in_match])

            if not settings.ELO_ONLY and not ba1v1tourney:
                RatingFactory.rating_class = GlickoRating
                glicko_teams = [SkillsTeam([(pa, GlickoRating(pa.get_rating(game, match_type_short).glicko, pa.get_rating(game, match_type_short).glicko_rd)) for pa in team]) for team in teams]
                glicko_matches = Matches([Match(glicko_teams, winner)])

                RatingFactory.rating_class = GaussianRating
                ts_teams = [SkillsTeam([(pa, GaussianRating(pa.get_rating(game, match_type_short).trueskill_mu, pa.get_rating(game, match_type_short).trueskill_sigma)) for pa in team]) for team in teams]
                ts_match = Match(ts_teams, winner)

            elo_game_info = EloGameInfo(initial_mean=1500, beta=200) # 200 will be doubled later -> use 400 as in original Elo algo
            glicko_game_info = GlickoGameInfo(initial_mean=1500, beta=1500/6)
            ts_game_info = TrueSkillGameInfo()

            elo_calculator = EloCalculator(k_factor=k_factor)
            elo_ratings = elo_calculator.new_ratings(elo_match, game_info=elo_game_info)
            if not settings.ELO_ONLY and not ba1v1tourney:
                glicko_calculator = GlickoCalculator()
                glicko_ratings = glicko_calculator.new_ratings(glicko_matches, game_info=glicko_game_info)
                #TODO: use glicko rating period
                ts_calculator = TwoPlayerTrueSkillCalculator()
                ts_ratings = ts_calculator.new_ratings(ts_match, game_info=ts_game_info)

            for pa in pas_in_match:
                if pas_in_match.filter(id__in=[p.id for p in pa.get_all_accounts()]).count() > 1:
                    # two accounts of the same player are in this match, none of them will get any rating
                    logger.info("found 2nd account of PA(%d) '%s'in replay(%d) '%s', not receiving rating", pa.pk, pa, replay.id, replay)
                    continue
                rating = pa.get_rating(game, match_type_short_b1t)
                rating.set_elo(elo_ratings.rating_by_id(pa))
                if not settings.ELO_ONLY and not ba1v1tourney:
                    rating.set_glicko(glicko_ratings.rating_by_id(pa))
                    rating.set_trueskill(ts_ratings.rating_by_id(pa))
                    rating_changes.append((pa, elo_ratings.rating_by_id(pa), glicko_ratings.rating_by_id(pa), ts_ratings.rating_by_id(pa)))
                else:
                    rating_changes.append((pa, elo_ratings.rating_by_id(pa), None, None))
                rating_history = RatingHistory.objects.create(playeraccount=pa, match=replay, algo_change="C", game=game, match_type=match_type_short_b1t)
                rating_history.set_elo(elo_ratings.rating_by_id(pa))
                if not settings.ELO_ONLY and not ba1v1tourney:
                    rating_history.set_glicko(glicko_ratings.rating_by_id(pa))
                    rating_history.set_trueskill(ts_ratings.rating_by_id(pa))
                    rating_history.algo_change="A"
                else:
                    rating_history.algo_change="E"
                rating_history.save()
        else:
            # use TrueSkill for Team and FFA matches
            RatingFactory.rating_class = GaussianRating
            ts_teams = [SkillsTeam([(pa, GaussianRating(pa.get_rating(game, match_type_short).trueskill_mu, pa.get_rating(game, match_type_short).trueskill_sigma)) for pa in team]) for team in teams]
            ts_match = Match(ts_teams, winner)

            game_info = TrueSkillGameInfo()
            if allyteams.count() == 2 and Team.objects.filter(allyteam=allyteams[0]).count() == Team.objects.filter(allyteam=allyteams[1]).count():
                ts_calculator = TwoTeamTrueSkillCalculator()
            else:
                # FactorGraphTrueSkillCalculator works for 1v1, Team and FFA games
                ts_calculator = FactorGraphTrueSkillCalculator()
            ts_ratings = ts_calculator.new_ratings(ts_match, game_info)

            for pa in pas_in_match:
                if pas_in_match.filter(id__in=[p.id for p in pa.get_all_accounts()]).count() > 1:
                    # two accounts of the same player are in this match, none of them will get any rating
                    logger.info("found 2nd account of PA(%d) '%s'in replay(%d) '%s', not receiving rating", pa.pk, pa, replay.id, replay)
                    continue
                pa.get_rating(game, match_type_short).set_trueskill(ts_ratings.rating_by_id(pa))
                rating_changes.append((pa, None, None, ts_ratings.rating_by_id(pa)))
                rating_history = RatingHistory.objects.create(playeraccount=pa, match=replay, algo_change="C", game=game, match_type=match_type_short)
                rating_history.set_trueskill(ts_ratings.rating_by_id(pa))
                rating_history.algo_change="T"
                rating_history.save()

    logger.debug("rated replay(%d | %s): %s", replay.pk, replay.gameID, replay)
    return rating_changes

def rate_1v1_tourney(replays, game, match_type):
    elo_corrections = dict()
    replays_rated = list()

    if match_type != "O":
        raise NotImplementedError("Only 1v1 tourney with Elo atm.")

    RatingFactory.rating_class = EloRating
    k_factor = 30
    elo_game_info = EloGameInfo(initial_mean=1500, beta=200) # 200 will be doubled later -> use 400 as in original Elo algo
    elo_calculator = EloCalculator(k_factor=k_factor)

    for replay in replays:
        if replay in replays_rated: continue
        if replay.notcomplete: raise RuntimeError("Replay(%d) %s is not complete, cannot compute."%(replay.pk, replay.gameID))

        pas = PlayerAccount.objects.filter(player__replay=replay, player__spectator=False)
        if pas.count() != 2: raise RuntimeError("Replay(%d) %s has !=2 players: %s."%(replay.pk, replay.gameID, pas))

        pa0 = pas[0]
        pa1 = pas[1]
        logger.debug("== %s (%f) vs %s (%f) ==", pa0.get_preffered_name(), pa0.get_rating(game, match_type).elo, pa1.get_preffered_name(), pa1.get_rating(game, match_type).elo)

        all_matches_of_pa0 = replays.filter(player__account=pa0, player__spectator=False)
        matches_of_pa0_vs_pa1 = all_matches_of_pa0.filter(player__account=pa1, player__spectator=False)

        exp_score_pa0_vs_pa1 = matches_of_pa0_vs_pa1.count() * elo_calculator.expected_score(pa0.get_rating(game, match_type).elo, pa1.get_rating(game, match_type).elo, elo_game_info)

        logger.debug("    matches: %s   (%s)", [int(m.id) for m in matches_of_pa0_vs_pa1], [m.gameID for m in matches_of_pa0_vs_pa1])
        logger.debug("    exp_score (%s): %d * %.2f = %.2f", pa0.get_preffered_name(), matches_of_pa0_vs_pa1.count(), elo_calculator.expected_score(pa0.get_rating(game, match_type).elo, pa1.get_rating(game, match_type).elo, elo_game_info), exp_score_pa0_vs_pa1)

        act_score_pa0_vs_pa1 = 0
        for match in matches_of_pa0_vs_pa1:
            allyteams = Allyteam.objects.filter(replay=match)
            if not allyteams[0].winner and not allyteams[1].winner:
                act_score_pa0_vs_pa1 += 0.5 # draw
            else:
                pa0_player = Player.objects.get(replay=match, account=pa0)
                allyteam_pa0 = pa0_player.team.allyteam
                if allyteam_pa0.winner:
                    act_score_pa0_vs_pa1 += 1
                # else: act_score_pa0_vs_pa1 += 0
        logger.debug("    act_score (%s): %.2f", pa0.get_preffered_name(), act_score_pa0_vs_pa1)

        elo_cor_pa0_vs_pa1 = k_factor * (act_score_pa0_vs_pa1 - exp_score_pa0_vs_pa1)
        logger.debug("    Elo correction (%s): %.2f", pa0.get_preffered_name(), elo_cor_pa0_vs_pa1)

        try:
            elo_corrections[pa0] += elo_cor_pa0_vs_pa1
        except KeyError:
            elo_corrections[pa0] = elo_cor_pa0_vs_pa1

        try:
            elo_corrections[pa1] -= elo_cor_pa0_vs_pa1
        except KeyError:
            elo_corrections[pa1] = -1 * elo_cor_pa0_vs_pa1

        logger.debug("    Elo correction sum for %s now: %.2f", pa0.get_preffered_name(), elo_corrections[pa0])
        logger.debug("    Elo correction sum for %s now: %.2f", pa1.get_preffered_name(), elo_corrections[pa1])

        replays_rated.extend(matches_of_pa0_vs_pa1)

    for pa, elo_correction in elo_corrections.iteritems():
        pa_rating = pa.get_rating(game, match_type)
        logger.debug("Elo update %s: %.2f + %.2f = %.2f", pa.get_preffered_name(), pa_rating.elo, elo_correction, pa_rating.elo+elo_correction)
        pa_rating.elo += elo_correction
        pa_rating.save()
        # store history into last match of tourney
        last_match = replays.order_by("-id")[0]
        RatingHistory.objects.create(playeraccount=pa, match=last_match, algo_change="E", game=game, match_type=match_type, elo = pa_rating.elo)

    logger.debug("*** all matches:   (%d) %s ***", replays.count(), [int(r.id) for r in replays.order_by("id")])
    li_ra = [int(r.id) for r in replays_rated]
    li_ra.sort()
    logger.debug("*** matches rated: (%d) %s ***", len(replays_rated), li_ra)
    logger.debug("*** nicks: ***")
    for pa in elo_corrections.iterkeys():
        try:
            logger.debug("    %s \t\t %s", pa.get_preffered_name(), pa.get_all_names())
        except:
            logger.error("getting names for %s", pa)
