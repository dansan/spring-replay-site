# This file is part of the "spring relay site / srs" program. It is published
# under the GPLv3.
#
# Copyright (C) 2012 Daniel Troeder (daniel #at# admin-box #dot# com)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.http import Http404, HttpResponse
from django.utils.html import strip_tags
from django.template import add_to_builtins
from django.core.urlresolvers import reverse

import MySQLdb

import logging
import gzip
import magic

from srs.models import *
from srs.common import all_page_infos
from srs.upload import save_tags, set_autotag, save_desc
from srs.sldb import privatize_skill, get_sldb_pref, set_sldb_pref, get_sldb_leaderboards, get_sldb_match_skills, get_sldb_player_ts_history_graphs
from srs.ajax_views import replay_filter
from srs.forms import GamePref

add_to_builtins('djangojs.templatetags.js')
logger = logging.getLogger(__package__)

def index(request):
    c = all_page_infos(request)
    if c.has_key("game_pref_obj"):
        replays = Replay.objects.filter(published=True, gametype__in=c["game_pref_obj"].gamerelease_set.values_list("name", flat=True))
    else:
        replays = Replay.objects.filter(published=True)
    c["replays"] = replays.order_by("-unixTime")[:settings.INDEX_REPLAY_RANGE]
    c["range"] = settings.INDEX_REPLAY_RANGE
    c["range_end"] = settings.INDEX_REPLAY_RANGE
    c["popular_replays"] = Replay.objects.order_by("-download_count")[:8]
    c["news"] = NewsItem.objects.filter(show=True).order_by('-pk')[:6]
    c["replay_details"] = False
    c["pageunique"] = reduce(lambda x, y: x+y, [str(r.pk) for r in c["replays"]])
    c["latest_comments"] = Comment.objects.filter(is_removed=False).order_by("-submit_date")[:5]
    return render_to_response('index.html', c, context_instance=RequestContext(request))

def index_replay_range(request, range_end, game_pref):
    c = all_page_infos(request)
    try:
        game_pref = int(game_pref)
    except:
        pass
    else:
        if not c.has_key("game_pref_obj") and game_pref > 0:
            c["game_pref"] = game_pref
            c["game_pref_obj"] = Game.objects.get(id=game_pref)
    c["range"] = settings.INDEX_REPLAY_RANGE
    c["range_end"] = int(range_end) + settings.INDEX_REPLAY_RANGE
    if c.has_key("game_pref_obj"):
        replays = Replay.objects.filter(published=True, gametype__in=c["game_pref_obj"].gamerelease_set.values_list("name", flat=True))
    else:
        replays = Replay.objects.filter(published=True)
    c["replays"] = replays.order_by("-unixTime")[int(range_end):c["range_end"]]
    return render_to_response('replay_index_boxes.html', c, context_instance=RequestContext(request))

def replay(request, gameID):
    c = all_page_infos(request)
    try:
        replay = Replay.objects.prefetch_related().get(gameID=gameID)
        c["replay"] = replay
    except:
        raise Http404("No replay with gameID '"+ strip_tags(gameID)+"' found.")

    if not replay.published:
        return render_to_response('replay_unpublished.html', c, context_instance=RequestContext(request))

    game = replay.game_release.game
    match_type = replay.match_type_short

    try:
        match_skills = get_sldb_match_skills([replay.gameID])
        if match_skills:
            match_skills = match_skills[0]
    except Exception, e:
        logger.exception("in get_sldb_match_skills(%s): %s", [replay.gameID], e)
        match_skills = {"status": 3}
        # ignore, we'll just use the old values from the DB in the view
    else:
        if match_skills and match_skills["status"] == 0:
            # update skill data in DB
            logger.debug("got match data from sldb")
            for player in match_skills["players"]:
                pa = player["account"]
                pa_skill = pa.get_rating(game, match_type)
                mu, si = player["skills"][1]
                if pa_skill.trueskill_mu != mu or pa_skill.trueskill_sigma != si:
                    try:
                        playername = Player.objects.get(account=pa, replay=replay).name
                    except:
                        playername = "??"
                    pa_skill.trueskill_mu = mu
                    pa_skill.trueskill_sigma = si
                    if pa_skill.playername == "" or pa_skill.playername == "??":
                        pa_skill.playername = playername
                    pa_skill.save()
                    defaults = {"match_date": replay.unixTime, "playername": playername, "trueskill_mu": mu, "trueskill_sigma": si}
                    rh, created = RatingHistory.objects.get_or_create(match=replay, game=game, match_type=match_type, playeraccount=pa, defaults=defaults)
                    if not created:
                        for k,v in defaults.items():
                            setattr(rh, k, v)
                        rh.save()
                if pa.sldb_privacy_mode != player["privacyMode"]:
                    pa.sldb_privacy_mode = player["privacyMode"]
                    pa.save()
                if replay.rated == False:
                    replay.rated = True
                    replay.save()
        else:
            # ignore, we'll just use the old values from the DB in the view
            logger.debug("no match data from SLDB")
            pass

    # fill cache prefetching all entries from DB in one call
    all_players = Player.objects.filter(replay=replay)
    allyteams = Allyteam.objects.filter(replay=replay)
    c["allyteams"] = []
    for at in allyteams:
        playeraccounts = PlayerAccount.objects.filter(player__team__allyteam=at).order_by("player__team__num")
        teams = Team.objects.filter(allyteam=at)
        players = all_players.filter(account__in=playeraccounts)
        players_w_rating = list()
        old_rating = 0
        new_rating = 0
        lobby_rank_sum = 0
        if replay.rated == False or replay.notcomplete or not players.exists() or not replay.game_release.game.sldb_name or all_players.filter(account__accountid=0).exists():
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
                    # use old method of DB lookups for currect and previous matchs DB entries
                    try:
                        pl_new = RatingHistory.objects.get(match=replay, playeraccount=pa, game=game, match_type=match_type).trueskill_mu
                    except:
                        # no rating on this replay
                        pl_new = None
                    try:
                        # find previous TS value
                        pl_old = RatingHistory.objects.filter(playeraccount=pa, game=game, match_type=match_type, match__unixTime__lt=replay.unixTime,).order_by("-match__unixTime")[0].trueskill_mu
                    except:
                        pl_old = None

                # privatize?
                if playeraccounts.count() > 2 or pa.sldb_privacy_mode == 0:
                    new_rating += pl_new if pl_new else 0
                    old_rating += pl_old if pl_old else 0
                else:
                    new_rating += privatize_skill(pl_new) if pl_new else 0
                    old_rating += privatize_skill(pl_old) if pl_old else 0

                if pa.sldb_privacy_mode != 0 and (not request.user.is_authenticated() or pa.accountid != request.user.userprofile.accountid):
                    if pl_new:
                        pl_new = privatize_skill(pl_new)
                    if pl_old:
                        pl_old = privatize_skill(pl_old)
                players_w_rating.append((all_players.get(account=pa, spectator=False), pl_old, pl_new))

        if teams:
            lobby_rank_sum = reduce(lambda x, y: x+y, [pl.rank for pl in all_players.filter(team__allyteam=at)], 0)
            c["allyteams"].append((at, players_w_rating, old_rating, new_rating, lobby_rank_sum))

    c["has_bot"] = replay.tags.filter(name="Bot").exists()
    c["specs"] = all_players.filter(replay=replay, spectator=True).order_by("id")
    c["upload_broken"] = UploadTmp.objects.filter(replay=replay).exists()
    c["mapoptions"] = MapOption.objects.filter(replay=replay).order_by("name")
    c["modoptions"] = ModOption.objects.filter(replay=replay).order_by("name")
    c["replay_details"] = True
    c["was_stopped"] = not allyteams.filter(winner=True).exists()
    c["is_draw"] = allyteams.filter(winner=True).count() > 1
    c["pagedescription"] = "%s %s %s match on %s (%s)"%(replay.num_players, replay.match_type, replay.game_release.game.name, replay.map_info.name, replay.unixTime)
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
        c["metadata"].append(("Size", "%d x %d"%(map_px_x, map_px_y)))
        if replay.map_info.metadata.has_key("MinWind") and replay.map_info.metadata.has_key("MaxWind"):
            c["metadata"].append(("Wind", "%d - %d"%(replay.map_info.metadata["metadata"]["MinWind"], replay.map_info.metadata["metadata"]["MaxWind"])))
        if replay.map_info.metadata.has_key("TidalStrength"):
            c["metadata"].append(("Tidal", str(replay.map_info.metadata["metadata"]["TidalStrength"])))
        for k,v in replay.map_info.metadata["metadata"].items():
            if type(v) == str and not v.strip():
                continue
            elif type(v) == list and not v:
                continue
            elif k.strip() in ["", "Width", "TidalStrength", "MapFileName", "MapMinHeight", "Type", "MapMaxHeight", "Resources", "Height", "MinWind", "MaxWind", "StartPos"]:
                # either already added above, or ignore uninteresting data
                continue
            else:
                c["metadata"].append((k.strip(), v))
        if replay.map_info.metadata.has_key("version") and replay.map_info.metadata["version"]:
            c["metadata"].append(("Version", replay.map_info.metadata["version"]))
    except Exception, e:
        c["metadata"].append(("Error", "Problem with metadata. Please report to Dansan."))
        logger.error("Problem with metadata (replay.id '%d'), replay.map_info.metadata: %s", replay.id, replay.map_info.metadata)
        logger.exception("Exception: %s", e)
    c["xtaward_heroes"] = XTAwards.objects.filter(replay=replay, isAlive=1)
    c["xtaward_los"]    = XTAwards.objects.filter(replay=replay, isAlive=0)

    return render_to_response('replay.html', c, context_instance=RequestContext(request))

def replay_by_id(request, replayid):
    try:
        r = Replay.objects.get(id=replayid)
        return HttpResponseRedirect(r.get_absolute_url())
    except:
        raise Http404("No replay with ID '"+ strip_tags(replayid)+"' found.")

@login_required
@never_cache
def edit_replay(request, gameID):
    from forms import EditReplayForm

    c = all_page_infos(request)
    try:
        replay = Replay.objects.prefetch_related().get(gameID=gameID)
        c["replay"] = replay
    except:
        raise Http404("No replay with ID '"+ strip_tags(gameID)+"' found.")

    if request.user != replay.uploader:
        return render_to_response('edit_replay_wrong_user.html', c, context_instance=RequestContext(request))

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
                        request.user, replay.gameID, replay.short_text, replay.title, replay.long_text, reduce(lambda x,y: x+", "+y, [t.name for t in Tag.objects.filter(replay=replay)]))
            return HttpResponseRedirect(replay.get_absolute_url())
    else:
        form = EditReplayForm({'short': replay.short_text, 'long_text': replay.long_text, 'tags': reduce(lambda x,y: x+", "+y, [t.name for t in Tag.objects.filter(replay=replay)])})
    c['form'] = form
    c["replay_details"] = True

    return render_to_response('edit_replay.html', c, context_instance=RequestContext(request))

def download(request, gameID):
    replay = get_object_or_404(Replay, gameID=gameID)

    replay.download_count += 1
    replay.save()

    path = replay.path+"/"+replay.filename
    try:
        filemagic = magic.from_file(path, mime=True)
    except IOError:
        errmsg = 'File for replay(%d) "%s" not found.' %(replay.id, replay)
        logger.error(errmsg)
        raise Http404(errmsg)
    if filemagic.endswith("gzip"):
        demofile = gzip.open(path, 'rb')
    else:
        demofile = open(path, "rb")
    if replay.filename.endswith(".gz"):
        filename = replay.filename[:-3]
    else:
        filename = replay.filename

    response = HttpResponse(demofile.read(), content_type='application/x-spring-demo')
    response['Content-Disposition'] = 'attachment; filename="%s"'%filename
    return response

def respect_privacy(request, accountid):
    """
    Check if the currently logged in user is allowed to see private TS data
    :param request: django request object - request.user is the website user
    :param accountid: int - user with the TrueSkill data that may be privacy protected
    :return: bool - if True: use only rounded numbers / don't show TS history graphs / etc
    """
    accountid = int(accountid)
    if request.user.is_authenticated() and accountid == request.user.get_profile().accountid:
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
        except:
            logger.exception("Could not retrieve privacyMode for accountid '%s' from SLDB.", accountid)
            privacy = True
    return privacy

def player(request, accountid):
    c = all_page_infos(request)
    accountid = int(accountid)
    pa = get_object_or_404(PlayerAccount, accountid=accountid)
    c['pagetitle'] = "Player "+pa.preffered_name
    c["pagedescription"] = "Statistics and match history of player %s"%pa.preffered_name
    c["playeraccount"] = pa
    c["PA"] = pa
    c["all_names"] = pa.get_names()

    if not respect_privacy(request, accountid):
        c["ts_history_games"] = pa.get_all_games_no_bots().exclude(sldb_name="")
    return render_to_response("player.html", c, context_instance=RequestContext(request))

def ts_history_graph(request, game_abbr, accountid, match_type):
    if respect_privacy(request, accountid):
        with open(settings.IMG_PATH+"/tsh_privacy.png", "rb") as pic:
            response = HttpResponse(pic.read(), content_type='image/png')
        return response
    path = str()
    accountid = int(accountid)
    if match_type not in ["1", "T", "F", "G", "L"]:
        logger.error("Bad argument 'match_type': '%s'.", match_type)
        path = settings.IMG_PATH+"/tsh_error.png"
    else:
        try:
            graphs = get_sldb_player_ts_history_graphs(game_abbr, accountid)
        except:
            logger.exception("in get_sldb_player_ts_history_graphs('%s', %d)", game_abbr, accountid)
            path = settings.IMG_PATH+"/tsh_error.png"
    if not path:
        path = graphs[SldbPlayerTSGraphCache.match_type2sldb_name[match_type]]
    with open(path, "rb") as pic:
        response = HttpResponse(pic.read(), content_type='image/png')
    return response

def hall_of_fame(request, abbreviation):
    c = all_page_infos(request)
    game = get_object_or_404(Game, abbreviation=abbreviation)

    if game.sldb_name != "":
        try:
            c["leaderboards"] = get_sldb_leaderboards(game)
        except Exception, e:
            logger.exception(e)
    else:
        c["errmsg"] = "No ratings available for this game. Please choose one from the menu."
        logger.error("%s (%s)", c["errmsg"], game)

    if abbreviation == "ZK":
        c["intro_text"] = ['<b>The official Hall of Fame of Zero-K is at <a href="http://zero-k.info/Ladders">http://zero-k.info/Ladders</a>.</b>']
    c["games"] = Game.objects.exclude(sldb_name="")
    c["ladders"] = [x[1] for x in RatingBase.MATCH_TYPE_CHOICES]
#    games_with_bawards = Game.objects.filter(gamerelease__name__in=BAwards.objects.values_list("replay__gametype", flat=True).distinct()).distinct()
#FIXME: show awards that belong to each game separately. for now only BA.
    games_with_bawards = Game.objects.filter(name="Balanced Annihilation")
    if game in games_with_bawards:
        try:
            sist = SiteStats.objects.get(id=1)
        except:
            update_stats()
            sist = SiteStats.objects.get(id=1)

        c["bawards"] = sist.bawards
        c["bawards_lu"] = sist.last_modified
    c["thisgame"] = game
    return render_to_response("hall_of_fame.html", c, context_instance=RequestContext(request))

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
    return render_to_response('settings.html', c, context_instance=RequestContext(request))

def all_comments(request):
    c = all_page_infos(request)
    return render_to_response('comments.html', c, context_instance=RequestContext(request))

@never_cache
def login(request):
    import django.contrib.auth
    from django.contrib.auth.forms import AuthenticationForm

    c = all_page_infos(request)
    nexturl = request.GET.get("next", "/")
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        form.fields["password"].max_length = 4096
        if form.is_valid():
            user = form.get_user()
            django.contrib.auth.login(request, user)
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
    return render_to_response('login.html', c, context_instance=RequestContext(request))

@never_cache
def logout(request):
    import django.contrib.auth

    username = str(request.user)
    # restore game_pref after logout
    game_pref = request.session.get("game_pref", None)
    django.contrib.auth.logout(request)
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
        return render_to_response('show_svg.html', c, context_instance=RequestContext(request))
    else:
        try:
            response = HttpResponse(media.media.read(), content_type=media.media_magic_mime)
            response['Content-Disposition'] = 'attachment; filename="%s"'%media.media_basename
            return response
        except IOError, e:
            logger.error("Cannot read media from ExtraReplayMedia(%d) of Replay(%d): media '%s'. Exception: %s" %(media.id, media.replay.id, media.media_basename, str(e)))
            raise Http404("Error reading '%s', please contact 'Dansan' in the springrts forum."%media.media_basename)

@login_required
@never_cache
def sldb_privacy_mode(request):
    from forms import SLDBPrivacyForm
    c = all_page_infos(request)

    accountid = request.user.userprofile.accountid
    try:
        c["current_privacy_mode"] = get_sldb_pref(accountid, "privacyMode")
    except:
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

    return render_to_response('sldb_privacy_mode.html', c, context_instance=RequestContext(request))

def browse_archive(request, bfilter):
    c = all_page_infos(request)

    for browse_filter in ["t_today", "t_yesterday", "t_this_month", "t_last_month", "t_this_year", "t_last_year", "t_ancient"]:
        c[browse_filter] = replay_filter(Replay.objects.all(), "date " + browse_filter)

    try:
        sist = SiteStats.objects.get(id=1)
    except:
        update_stats()
        sist = SiteStats.objects.get(id=1)

    tags              = map(lambda x: (Tag.objects.get(id=int(x.split(".")[0])), x.split(".")[1]), sist.tags.split('|'))
    c["top_tags"]     = list()
    for t in range(0, 12, 3):
        if t+2 > len(tags): break
        c["top_tags"].append((tags[t], tags[t+1], tags[t+2]))
    maps              = map(lambda x: (Map.objects.get(id=int(x.split(".")[0])), x.split(".")[1]), sist.maps.split('|'))
    c["top_maps"]     = list()
    for r in range(0, 8, 2):
        if r+1 > len(maps): break
        c["top_maps"].append((maps[r], maps[r+1]))
    c["top_players"]  = map(lambda x: (PlayerAccount.objects.get(id=int(x.split(".")[0])), x.split(".")[1]), sist.active_players.split('|'))
    c["all_games"]    = map(lambda x: (Game.objects.get(id=int(x.split(".")[0])), x.split(".")[1]), sist.games.split('|'))
    c["replays_num"]  = Replay.objects.count()
    c["gr_all"]       = GameRelease.objects.all()
    c["tags_all"]     = Tag.objects.all()
    c["maps_all"]     = Map.objects.all()
    c["pa_num"]       = PlayerAccount.objects.exclude(accountid__lte=0).count()
    c["ah_num"]       = Replay.objects.values("autohostname").distinct().count()
    c["user_num"]     = len([user for user in User.objects.all() if user.replays_uploaded() > 0])
    c["first_replay"] = Replay.objects.first()
    c["last_replay"]  = Replay.objects.last()
    hosts = dict()
    for host in Replay.objects.values_list("autohostname", flat=True):
        if host:
            try:
                hosts[host] += 1
            except:
                hosts[host] = 0
    c["autohosts"]    = [(name, count) for name, count in hosts.items() if count > 0]
    c["autohosts"].sort(key=operator.itemgetter(1), reverse=True)
    c["uploaders"]    = [(user.username, user.replays_uploaded()) for user in User.objects.all() if user.replays_uploaded() > 0]
    c["uploaders"].sort(key=operator.itemgetter(1), reverse=True)

    if bfilter and bfilter.strip():
        bfilter = str(MySQLdb.escape_string(bfilter))
        args = bfilter.split("/")
        filters_ = map(lambda x: x.split("="), args)
        # only accept "date=1224/tag=8v8" etc
        c["filters"] = list()
        have = list()
        for filter_ in filters_:
            if len(filter_) == 2 and filter_[1].strip() and filter_[0] in ["date", "map", "tag", "game", "gameversion", "player", "autohost", "uploader" ] and filter_[0] not in have:
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
                        raise Exception("unknown filter type '%s'"%filter_[0])
                    # all fine, add filter
                    c["filters"].append((filter_[0], filter_[1]))
                    have.append(filter_[0])
                except Exception, e:
                    # object doesnt exist
                    logger.debug("invalid filter_: '%s' Exception: %s", filter_, e)
    else:
        c["filters"] = ""
    return render_to_response('browse_archive.html', c, context_instance=RequestContext(request))
