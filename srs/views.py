# This file is part of the "spring relay site / srs" program. It is published
# under the GPLv3.
#
# Copyright (C) 2016 Daniel Troeder (daniel #at# admin-box #dot# com)
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import logging
import gzip
import magic
import re
import operator

import MySQLdb

from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login as django_contrib_auth_login, logout as django_contrib_auth_logout
from django.views.decorators.cache import never_cache
from django.http import Http404, HttpResponse
from django.utils.html import strip_tags
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django_comments.models import Comment

from srs.models import Allyteam, ExtraReplayMedia, Game, GameRelease, Map, MapOption, ModOption, NewsItem, Player, PlayerAccount, RatingBase, RatingHistory, Replay, SiteStats, SldbPlayerTSGraphCache, Tag, Team, UploadTmp, XTAwards, get_owner_list, update_stats
from srs.common import all_page_infos
from srs.upload import save_tags, set_autotag, save_desc
from srs.sldb import privatize_skill, get_sldb_pref, set_sldb_pref, get_sldb_leaderboards, get_sldb_match_skills, get_sldb_player_ts_history_graphs, SLDBConnectionError
from srs.ajax_views import replay_filter
from srs.forms import EditReplayForm, GamePref, SLDBPrivacyForm
from srs.utils import fix_missing_winner

#add_to_builtins('djangojs.templatetags.js')
logger = logging.getLogger("srs.views")

gameid_re = re.compile("^[0-9a-f]{32}$")


def index(request):
    c = all_page_infos(request)
    if "game_pref_obj" in c:
        replays = Replay.objects.filter(published=True,
                                        gametype__in=c["game_pref_obj"].gamerelease_set.values_list("name", flat=True))
    else:
        replays = Replay.objects.filter(published=True)
    c["replays"] = replays.order_by("-upload_date")[:settings.INDEX_REPLAY_RANGE]
    c["range"] = settings.INDEX_REPLAY_RANGE
    c["range_end"] = settings.INDEX_REPLAY_RANGE
    c["popular_replays"] = Replay.objects.order_by("-download_count")[:8]
    c["news"] = NewsItem.objects.filter(show=True).order_by('-pk')[:6]
    c["replay_details"] = False
    c["latest_comments"] = Comment.objects.filter(is_removed=False).order_by("-submit_date")[:5]
    return render(request, 'index.html', c)


def index_replay_range(request, range_end, game_pref):
    c = all_page_infos(request)
    try:
        game_pref = int(game_pref)
    except (TypeError, ValueError):
        pass
    else:
        if "game_pref_obj" not in c and game_pref > 0:
            c["game_pref"] = game_pref
            c["game_pref_obj"] = Game.objects.get(id=game_pref)
    c["range"] = settings.INDEX_REPLAY_RANGE
    c["range_end"] = int(range_end) + settings.INDEX_REPLAY_RANGE
    if "game_pref_obj"in c:
        replays = Replay.objects.filter(published=True,
                                        gametype__in=c["game_pref_obj"].gamerelease_set.values_list("name", flat=True))
    else:
        replays = Replay.objects.filter(published=True)
    c["replays"] = replays.order_by("-upload_date")[int(range_end):c["range_end"]]
    return render(request, 'replay_index_boxes.html', c)


def replay(request, gameID):
    c = all_page_infos(request)

    if not gameid_re.findall(gameID):
        raise Http404("Malformed gameID: %r." % gameID)

    try:
        replay = Replay.objects.prefetch_related().get(gameID=gameID)
        c["replay"] = replay
        c["comment_obj"] = replay
    except ObjectDoesNotExist:
        raise Http404("No replay with gameID '" + strip_tags(gameID) + "' found.")

    if not replay.published:
        return render(request, 'replay_unpublished.html', c)

    game = replay.game_release.game
    match_type = replay.match_type_short

    sldb_connection_error = False
    try:
        match_skills = get_sldb_match_skills([replay.gameID])
        if match_skills:
            match_skills = match_skills[0]
    except SLDBConnectionError as exc:
        sldb_connection_error = True
        logger.error("get_sldb_match_skills(%s): %s", [replay.gameID], exc)
        match_skills = {"status": 3}
        # ignore, we'll just use the old values from the DB in the view
    else:
        if match_skills and match_skills["status"] == 0:
            # update skill data in DB
            logger.debug("got match data for %s from sldb", replay)
            for player in match_skills["players"]:
                pa = player["account"]
                pa_skill = pa.get_rating(game, match_type)
                mu, si = player["skills"][1]
                if pa_skill.trueskill_mu != mu or pa_skill.trueskill_sigma != si:
                    try:
                        playername = Player.objects.get(account=pa, replay=replay, spectator=False).name
                    except ObjectDoesNotExist:
                        playername = "??"
                    pa_skill.trueskill_mu = mu
                    pa_skill.trueskill_sigma = si
                    if pa_skill.playername == "" or pa_skill.playername == "??":
                        pa_skill.playername = playername
                    pa_skill.save()
                    defaults = dict(
                        match_date=replay.unixTime,
                        playername=playername,
                        trueskill_mu=mu,
                        trueskill_sigma=si
                    )
                    RatingHistory.objects.update_or_create(match=replay,
                                                           game=game,
                                                           match_type=match_type,
                                                           playeraccount=pa,
                                                           defaults=defaults)
                if pa.sldb_privacy_mode != player["privacyMode"]:
                    pa.sldb_privacy_mode = player["privacyMode"]
                    pa.save()
                if not replay.rated:
                    replay.rated = True
                    replay.save()
        else:
            # ignore, we'll just use the old values from the DB in the view
            logger.debug("no match data from SLDB")
            pass

    # fill cache prefetching all entries from DB in one call
    all_players = Player.objects.filter(replay=replay)
    allyteams = Allyteam.objects.filter(replay=replay)
    if not allyteams.filter(winner=True).exists() or (
            replay.upload_date.year >= 2016 and allyteams.filter(winner=True, num=0).exists()) and not sldb_connection_error:
        # workaround for issue #89: guess winner from ratings
        fix_missing_winner(replay)

    c["allyteams"] = []
    match_rating_history = RatingHistory.objects.filter(match=replay, match_type=match_type)
    [entry for entry in match_rating_history]  # prefetch all ratings of this match by hitting the DB only once
    for at in allyteams:
        playeraccounts = PlayerAccount.objects.filter(player__team__allyteam=at).order_by("player__team__num")
        teams = Team.objects.filter(allyteam=at)
        players = all_players.filter(account__in=playeraccounts)
        players_w_rating = list()
        old_rating = 0
        new_rating = 0
        lobby_rank_sum = 0
        if replay.rated == False or replay.notcomplete or not players.exists() or not replay.game_release.game.sldb_name or all_players.filter(
                account__accountid=0).exists():
            # notcomplete, no SLDB rating or bot present -> no rating
            players_w_rating = [(player, None, None) for player in players]
        else:
            # TrueSkill ratings
            for pa in playeraccounts:
                if match_skills and match_skills["status"] == 0:
                    # use SLDB-provided values
                    def _get_players_skills(pa):
                        for pl in match_skills["players"]:
                            if pl["account"] == pa: return pl

                    pl = _get_players_skills(pa)
                    pl_new = pl["skills"][1][0]
                    pl_old = pl["skills"][0][0]
                else:
                    # use old method of DB lookups for current and previous matchs DB entries
                    try:
                        pl_new = match_rating_history.get(playeraccount=pa).trueskill_mu
                    except ObjectDoesNotExist:
                        # no rating on this replay
                        pl_new = None
                    try:
                        # find previous TS value
                        pl_old = RatingHistory.objects.filter(playeraccount=pa, game=game, match_type=match_type,
                                                              match__unixTime__lt=replay.unixTime).order_by(
                            "-match__unixTime")[0].trueskill_mu
                    except IndexError:
                        pl_old = 25  # default value for new players

                # privatize?
                if playeraccounts.count() > 2 or pa.sldb_privacy_mode == 0:
                    new_rating += pl_new if pl_new else 0
                    old_rating += pl_old if pl_old else 0
                else:
                    new_rating += privatize_skill(pl_new) if pl_new else 0
                    old_rating += privatize_skill(pl_old) if pl_old else 0

                if pa.sldb_privacy_mode != 0 and (
                    not request.user.is_authenticated() or pa.accountid != request.user.userprofile.accountid):
                    if pl_new:
                        pl_new = privatize_skill(pl_new)
                    if pl_old:
                        pl_old = privatize_skill(pl_old)
                players_w_rating.append((all_players.get(account=pa, spectator=False), pl_old, pl_new))

        if teams:
            lobby_rank_sum = reduce(lambda x, y: x + y, [pl.rank for pl in all_players.filter(team__allyteam=at)], 0)
            c["allyteams"].append((at, players_w_rating, old_rating, new_rating, lobby_rank_sum))

    c["has_bot"] = replay.tags.filter(name="Bot").exists()
    c["specs"] = all_players.filter(replay=replay, spectator=True).order_by("id")
    c["upload_broken"] = UploadTmp.objects.filter(replay=replay).exists()
    c["mapoptions"] = MapOption.objects.filter(replay=replay).order_by("name")
    c["modoptions"] = ModOption.objects.filter(replay=replay).order_by("name")
    c["replay_details"] = True
    c["was_stopped"] = not allyteams.filter(winner=True).exists()
    if c["was_stopped"]:
        logger.info("was_stopped=True: allyteams=%r replay=%r", allyteams, replay)
    c["is_draw"] = allyteams.filter(winner=True).count() > 1
    c["pagedescription"] = "%s %s %s match on %s (%s)" % (
    replay.num_players, replay.match_type, replay.game_release.game.name, replay.map_info.name, replay.unixTime)
    c["replay_owners"] = get_owner_list(replay.uploader)
    c["extra_media"] = ExtraReplayMedia.objects.filter(replay=replay)
    c["known_video_formats"] = ["video/webm", "video/mp4", "video/ogg", "video/x-flv", "application/ogg"]
    c["has_video"] = c["extra_media"].filter(media_magic_mime__in=c["known_video_formats"]).exists()
    c["metadata"] = list()
    if replay.map_info.width > 128:
        # api.springfiles.com returnd pixel size
        map_px_x = replay.map_info.width / 512
        map_px_y = replay.map_info.height / 512
    else:
        # api.springfiles.com returnd Spring Map Size
        map_px_x = replay.map_info.width
        map_px_y = replay.map_info.height
    try:
        c["metadata"].append(("Size", "{} x {}".format(map_px_x, map_px_y)))
        try:
            c["metadata"].append(("Wind", "{} - {}".format(replay.map_info.metadata["metadata"]["MinWind"],
                                                           replay.map_info.metadata["metadata"]["MaxWind"])))
        except KeyError:
            pass
        try:
            c["metadata"].append(("Tidal", str(replay.map_info.metadata["metadata"]["TidalStrength"])))
        except KeyError:
            pass
        for k, v in replay.map_info.metadata["metadata"].items():
            if type(v) == str and not v.strip():
                continue
            elif type(v) == list and not v:
                continue
            elif k.strip() in ["", "Width", "TidalStrength", "MapFileName", "MapMinHeight", "Type", "MapMaxHeight",
                               "Resources", "Height", "MinWind", "MaxWind", "StartPos"]:
                # either already added above, or ignore uninteresting data
                continue
            else:
                c["metadata"].append((k.strip(), v))
        try:
            if replay.map_info.metadata["version"]:
                c["metadata"].append(("Version", replay.map_info.metadata["version"]))
        except KeyError:
            pass
    except Exception as exc:
        c["metadata"].append(("Error", "Problem with metadata. Please report to Dansan."))
        logger.error("FIXME: to broad exception handling.")
        logger.error("Problem with metadata (replay.id '%d'), replay.map_info.metadata: %s", replay.id,
                     replay.map_info.metadata)
        logger.exception("Exception: %s", exc)
    c["xtaward_heroes"] = XTAwards.objects.filter(replay=replay, isAlive=1)
    c["xtaward_los"] = XTAwards.objects.filter(replay=replay, isAlive=0)

    page_history = request.session.get("page_history")
    if page_history and isinstance(page_history, list):
        # check data (session data is user input)
        for page in list(page_history):
            if not gameid_re.findall(page):
                page_history.remove(page)
        if gameID not in page_history:
            if len(page_history) > 4:
                page_history.remove(page)
            page_history.insert(0, gameID)
    else:
        page_history = [gameID]
    request.session["page_history"] = page_history

    return render(request, 'replay.html', c)


def replay_by_id(request, replayid):
    try:
        r = Replay.objects.get(id=replayid)
        return HttpResponseRedirect(r.get_absolute_url())
    except ObjectDoesNotExist:
        raise Http404("No replay with ID '" + strip_tags(replayid) + "' found.")


@login_required
@never_cache
def edit_replay(request, gameID):
    c = all_page_infos(request)
    try:
        replay = Replay.objects.prefetch_related().get(gameID=gameID)
        c["replay"] = replay
    except ObjectDoesNotExist:
        raise Http404("No replay with ID '{}' found.".format(strip_tags(gameID)))

    if request.user != replay.uploader:
        return render(request, 'edit_replay_wrong_user.html', c)

    if request.method == 'POST':
        form = EditReplayForm(request.POST)
        if form.is_valid():
            short = request.POST['short']
            long_text = request.POST['long_text']
            tags = request.POST['tags']

            for tag in replay.tags.all():
                if tag.replay_count == 1 and tag.pk > 10:
                    # this tag was used only by this replay and is not one of the default ones (see srs/sql/tag.sql)
                    tag.delete()
            replay.tags.clear()
            autotag = set_autotag(replay)
            save_tags(replay, tags)
            save_desc(replay, short, long_text, autotag)
            replay.save()
            logger.info("User '%s' modified replay '%s': short: '%s' title:'%s' long_text:'%s' tags:'%s'",
                        request.user, replay.gameID, replay.short_text, replay.title, replay.long_text,
                        ", ".join(Tag.objects.filter(replay=replay).values_list("name", flat=True)))
            return HttpResponseRedirect(replay.get_absolute_url())
    else:
        form = EditReplayForm({'short': replay.short_text, 'long_text': replay.long_text,
                               'tags': ", ".join(Tag.objects.filter(replay=replay).values_list("name", flat=True))})
    c['form'] = form
    c["replay_details"] = True

    return render(request, 'edit_replay.html', c)


def download(request, gameID):
    replay = get_object_or_404(Replay, gameID=gameID)

    replay.download_count += 1
    replay.save()

    path = replay.path + "/" + replay.filename
    try:
        filemagic = magic.from_file(path, mime=True)
    except IOError:
        errmsg = 'File for replay(%d) "%s" not found.' % (replay.id, replay)
        logger.error(errmsg)
        raise Http404(errmsg)
    if filemagic.endswith("gzip") and not replay.filename.endswith(".sdfz"):
        demofile = gzip.open(path, 'rb')
    else:
        demofile = open(path, "rb")
    if replay.filename.endswith(".gz"):
        filename = replay.filename[:-3]
    else:
        filename = replay.filename

    response = HttpResponse(demofile.read(), content_type='application/x-spring-demo')
    response['Content-Disposition'] = 'attachment; filename="%s"' % filename
    return response


def respect_privacy(request, accountid):
    """
    Check if the currently logged in user is allowed to see private TS data
    :param request: django request object - request.user is the website user
    :param accountid: int - user with the TrueSkill data that may be privacy protected
    :return: bool - if True: use only rounded numbers / don't show TS history graphs / etc
    """
    accountid = int(accountid)
    if request.user.is_authenticated() and accountid == request.user.userprofile.accountid:
        # if the logged in user has the same accountid as the parameter accountid -> no privacy protection
        privacy = False
    else:
        # request privacyMode of player from SLDB
        try:
            privacy_mode = get_sldb_pref(accountid, "privacyMode")
            if privacy_mode == "0":
                privacy = False
            else:
                privacy = True
        except SLDBConnectionError as exc:
            logger.error("Could not retrieve privacyMode for accountid '%s' from SLDB: %s", accountid, exc)
            privacy = True
    return privacy


def player(request, accountid):
    c = all_page_infos(request)
    accountid = int(accountid)
    pa = get_object_or_404(PlayerAccount, accountid=accountid)
    c['pagetitle'] = "Player " + pa.preffered_name
    c["pagedescription"] = "Statistics and match history of player %s" % pa.preffered_name
    c["playeraccount"] = pa
    c["PA"] = pa
    c["all_names"] = pa.get_names()
    bawards = pa.bawards
    if any(pa.bawards.values()):
        c["bawards"] = bawards
    xtawards = pa.xtawards
    if any(xtawards):
        c["xtawards"] = xtawards

    if not respect_privacy(request, accountid):
        c["ts_history_games"] = pa.get_all_games_no_bots().exclude(sldb_name="")
    return render(request, "player.html", c)


def ts_history_graph(request, game_abbr, accountid, match_type):
    if respect_privacy(request, accountid):
        with open(settings.IMG_PATH + "/tsh_privacy.png", "rb") as pic:
            response = HttpResponse(pic.read(), content_type='image/png')
        return response
    path = str()
    accountid = int(accountid)
    if match_type not in ["1", "T", "F", "G", "L"]:
        logger.error("Bad argument 'match_type': '%s'.", match_type)
        path = settings.IMG_PATH + "/tsh_error.png"
    else:
        try:
            graphs = get_sldb_player_ts_history_graphs(game_abbr, accountid)
        except SLDBConnectionError as exc:
            logger.error("get_sldb_player_ts_history_graphs(%r, %d): %s", game_abbr, accountid, exc)
            path = settings.IMG_PATH + "/tsh_error.png"
    if not path:
        path = graphs[SldbPlayerTSGraphCache.match_type2sldb_name[match_type]]
    with open(path, "rb") as pic:
        response = HttpResponse(pic.read(), content_type='image/png')
    return response


def hall_of_fame(request, abbreviation):
    c = all_page_infos(request)
    game = get_object_or_404(Game, abbreviation=abbreviation)

    if game.sldb_name == "ZK":
        pass
    elif game.sldb_name != "":
        try:
            c["leaderboards"] = get_sldb_leaderboards(game)
        except SLDBConnectionError as exc:
            logger.error("get_sldb_leaderboards(%r): %s", game, exc)
    else:
        c["errmsg"] = "No ratings available for this game. Please choose one from the menu."
        logger.error("%s (%s)", c["errmsg"], game)

    if abbreviation == "ZK":
        c["intro_text"] = ['<b>The official Hall of Fame of Zero-K is at <a '
                           'href="http://zero-k.info/Ladders">http://zero-k.info/Ladders</a>.</b><br/>No rating '
                           'records are kept on this site anymore.']
    c["games"] = Game.objects.exclude(sldb_name="")
    c["ladders"] = [x[1] for x in RatingBase.MATCH_TYPE_CHOICES]
    #    games_with_bawards = Game.objects.filter(gamerelease__name__in=BAwards.objects.values_list("replay__gametype", flat=True).distinct()).distinct()
    # FIXME: show awards that belong to each game separately. for now only BA.
    games_with_bawards = Game.objects.filter(name="Balanced Annihilation")
    if game in games_with_bawards:
        try:
            sist = SiteStats.objects.get(id=1)
        except ObjectDoesNotExist:
            update_stats()
            sist = SiteStats.objects.get(id=1)

        c["bawards"] = sist.bawards
        c["bawards_lu"] = sist.last_modified
    c["thisgame"] = game
    return render(request, "hall_of_fame.html", c)


@login_required
@never_cache
def user_settings(request):
    # TODO:
    c = all_page_infos(request)
    up = request.user.userprofile
    if request.method == 'POST':
        game_pref_form = GamePref(request.POST)
        if game_pref_form.is_valid():
            up.game_pref_fixed = not game_pref_form.cleaned_data["auto"]
            if game_pref_form.cleaned_data["game_choice"]:
                up.game_pref = int(game_pref_form.cleaned_data["game_choice"])
            else:
                up.game_pref = request.session.get("game_pref", None)
            up.save()
            request.session["game_pref"] = up.game_pref
    else:
        game_pref_form = GamePref(initial={"auto": not up.game_pref_fixed, "game_choice": up.game_pref})
    c["game_pref_form"] = game_pref_form
    return render(request, 'settings.html', c)


def all_comments(request):
    c = all_page_infos(request)
    return render(request, 'comments.html', c)


@never_cache
def login(request):
    c = all_page_infos(request)
    nexturl = request.GET.get("next", "/")
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        form.fields["password"].max_length = 4096
        if form.is_valid():
            user = form.get_user()
            django_contrib_auth_login(request, user)
            logger.info("Logged in user '%s' (%s) a.k.a '%s'", user.username, user.last_name, user.userprofile.aliases)
            if request.user.userprofile.game_pref_fixed or request.session.get("game_pref", 0) == 0:
                # if pref was set explicitely, always set cookie according to profile
                # or if no cookie set, use profiles setting (even if 0)
                request.session["game_pref"] = request.user.userprofile.game_pref
            else:
                # cookie is already set (!=0), overwrite users pref as it's not fixed
                try:
                    request.user.userprofile.game_pref = int(request.session["game_pref"])
                    request.user.userprofile.save()
                except ValueError:
                    # not int, ignore
                    pass
            return HttpResponseRedirect(nexturl)
        else:
            logger.info("login error: %s", form.errors)
    else:
        form = AuthenticationForm()
    c["next"] = nexturl
    c['form'] = form
    form.fields["password"].max_length = 4096
    return render(request, 'login.html', c)


@never_cache
def logout(request):

    username = str(request.user)
    # restore game_pref after logout
    game_pref = request.session.get("game_pref", None)
    django_contrib_auth_logout(request)
    logger.info("Logged out user '%s'", username)
    if game_pref:
        request.session["game_pref"] = game_pref
    nexturl = request.GET.get('next')
    if nexturl:
        dest = nexturl
    else:
        dest = "/"
    return HttpResponseRedirect(dest)


def media(request, mediaid):
    media = get_object_or_404(ExtraReplayMedia, id=mediaid)
    if media.media_magic_mime == "image/svg+xml":
        c = all_page_infos(request)
        c["media"] = media
        return render(request, 'show_svg.html', c)
    else:
        try:
            response = HttpResponse(media.media.read(), content_type=media.media_magic_mime)
            response['Content-Disposition'] = 'attachment; filename="%s"' % media.media_basename
            return response
        except IOError, e:
            logger.error("Cannot read media from ExtraReplayMedia(%d) of Replay(%d): media '%s'. Exception: %s" % (
                media.id, media.replay.id, media.media_basename, str(e)))
            raise Http404("Error reading '%s', please contact 'Dansan' in the springrts forum." % media.media_basename)


@login_required
@never_cache
def sldb_privacy_mode(request):
    c = all_page_infos(request)

    accountid = request.user.userprofile.accountid
    try:
        c["current_privacy_mode"] = get_sldb_pref(accountid, "privacyMode")
    except SLDBConnectionError as exc:
        logger.error("get_sldb_pref(%r, \"privacyMode\"): %s", accountid, exc)
        c["current_privacy_mode"] = -1
    logger.debug("current_privacy_mode: %s (user: %s)", str(c["current_privacy_mode"]), request.user)

    if request.method == 'POST':
        #
        # POST
        #
        form = SLDBPrivacyForm(request.POST)
        if form.is_valid():
            c["in_post"] = True
            new_mode = int(form.cleaned_data["mode"])
            logger.debug("new_mode: %d (user: %s)", new_mode, request.user)
            try:
                sldb_pref = set_sldb_pref(accountid, "privacyMode", str(new_mode))
            except:
                logger.exception("FIXME: to broad exception handling.")
                c["new_privacy_mode"] = -1
            else:
                c["new_privacy_mode"] = new_mode
            logger.debug("new_privacy_mode: %d (user: %s)", new_mode, request.user)
    else:
        #
        # GET
        #
        form = SLDBPrivacyForm({'mode': c["current_privacy_mode"]})

    c['form'] = form

    return render(request, 'sldb_privacy_mode.html', c)


def browse_archive(request, bfilter):
    c = all_page_infos(request)

    for browse_filter in ["t_today", "t_yesterday", "t_this_month", "t_last_month", "t_this_year", "t_last_year",
                          "t_ancient"]:
        c[browse_filter] = replay_filter(Replay.objects.all(), "date " + browse_filter)

    try:
        sist = SiteStats.objects.get(id=1)
    except ObjectDoesNotExist:
        sist = update_stats()

    tags = map(lambda x: (Tag.objects.get(id=int(x.split(".")[0])), x.split(".")[1]), sist.tags.split('|'))
    c["top_tags"] = list()
    for t in range(0, 12, 3):
        if t + 3 > len(tags): break
        c["top_tags"].append((tags[t], tags[t + 1], tags[t + 2]))
    maps = map(lambda x: (Map.objects.get(id=int(x.split(".")[0])), x.split(".")[1]), sist.maps.split('|'))
    c["top_maps"] = list()
    for r in range(0, 8, 2):
        if r + 2 > len(maps): break
        c["top_maps"].append((maps[r], maps[r + 1]))
    c["top_players"] = map(lambda x: (PlayerAccount.objects.get(id=int(x.split(".")[0])), x.split(".")[1]),
                           sist.active_players.split('|'))
    c["all_games"] = map(lambda x: (Game.objects.get(id=int(x.split(".")[0])), x.split(".")[1]), sist.games.split('|'))
    c["replays_num"] = Replay.objects.count()
    c["gr_all"] = GameRelease.objects.all()
    c["tags_all"] = Tag.objects.all()
    c["maps_all"] = Map.objects.all()
    c["pa_num"] = PlayerAccount.objects.exclude(accountid__lte=0).count()
    c["ah_num"] = Replay.objects.values("autohostname").distinct().count()
    c["user_num"] = len([user for user in User.objects.all() if user.replays_uploaded() > 0])
    c["first_replay"] = Replay.objects.first()
    c["last_replay"] = Replay.objects.last()
    hosts = dict()
    for host in Replay.objects.values_list("autohostname", flat=True):
        if host:
            try:
                hosts[host] += 1
            except KeyError:
                hosts[host] = 0
    c["autohosts"] = [(name, count) for name, count in hosts.items() if count > 0]
    c["autohosts"].sort(key=operator.itemgetter(1), reverse=True)
    c["uploaders"] = [(user.username, user.replays_uploaded()) for user in User.objects.all() if
                      user.replays_uploaded() > 0]
    c["uploaders"].sort(key=operator.itemgetter(1), reverse=True)

    if bfilter and bfilter.strip():
        bfilter = str(MySQLdb.escape_string(bfilter))
        args = bfilter.split("/")
        filters_ = map(lambda x: x.split("="), args)
        # only accept "date=1224/tag=8v8" etc
        c["filters"] = list()
        have = list()
        for filter_ in filters_:
            if len(filter_) == 2 and filter_[1].strip() and filter_[0] in ["date", "map", "tag", "game", "gameversion",
                                                                           "player", "autohost", "uploader"] and \
                            filter_[0] not in have:
                try:
                    if filter_[0] == "date":
                        pass
                    elif filter_[0] == "map":
                        c["map_name"] = Map.objects.get(id=filter_[1]).name
                    elif filter_[0] == "tag":
                        Tag.objects.get(id=filter_[1])
                    elif filter_[0] == "game":
                        Game.objects.get(id=filter_[1])
                    elif filter_[0] == "gameversion":
                        gr = GameRelease.objects.get(id=filter_[1])
                        c["game_abbreviation"] = gr.game.abbreviation + " " + gr.version
                    elif filter_[0] == "player":
                        PlayerAccount.objects.get(id=filter_[1])
                    elif filter_[0] == "autohost":
                        Replay.objects.filter(autohostname=filter_[1])[0]
                    elif filter_[0] == "uploader":
                        Replay.objects.filter(uploader__username=filter_[1])[0]
                    else:
                        raise Exception("unknown filter type '%s'" % filter_[0])
                    # all fine, add filter
                    c["filters"].append((filter_[0], filter_[1]))
                    have.append(filter_[0])
                except Exception as exc:
                    # object doesnt exist
                    logger.exception("FIXME: to broad exception handling.")
                    logger.debug("invalid filter_: '%s' Exception: %s", filter_, exc)
    else:
        c["filters"] = ""
    return render(request, 'browse_archive.html', c)
