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
from django.views.decorators.cache import never_cache, cache_page
from django.http import Http404, HttpResponse
from django.contrib.comments import Comment
from django.views.decorators.cache import cache_control
from django.db.models import Max
from django.contrib.admin.views.decorators import staff_member_required
from django.core.urlresolvers import reverse
from django.utils.html import strip_tags

from dajax.core import Dajax
from dajaxice.decorators import dajaxice_register

import logging
from types import StringTypes
import datetime
import gzip
import magic

from models import *
from common import all_page_infos
from tables import *
from upload import save_tags, set_autotag, save_desc
from sldb import get_sldb_playerskill, privatize_skill, demoskill2float, get_sldb_pref, set_sldb_pref, get_sldb_player_stats, get_sldb_leaderboards

logger = logging.getLogger(__package__)

@cache_control(must_revalidate=True, max_age=60)
def index(request):
    c = all_page_infos(request)
    c["newest_replays"] = Replay.objects.all().order_by("-unixTime")[:10]
    c["news"] = NewsItem.objects.filter(show=True).order_by('-pk')[:6]
    c["replay_details"] = False
    c["pageunique"] = reduce(lambda x, y: x+y, [str(r.pk) for r in c["newest_replays"]])
    return render_to_response('index.html', c, context_instance=RequestContext(request))

def replays(request):
    replays = Replay.objects.all()
    return replay_table(request, replays, "List of all %d matches"%Replay.objects.count(), ext={"pagedescription": "list of all replays."})

def replay_table(request, replays, title, template="lists.html", form=None, ext=None, order_by=None):
    from django_tables2 import RequestConfig

    c = all_page_infos(request)
    if ext:
        for k,v in ext.items():
            c[k] = v

    replays = replays.select_related('uploader').order_by("-upload_date")

    if order_by:
        table = ReplayTable(replays, prefix="r-", order_by=order_by)
    else:
        table = ReplayTable(replays, prefix="r-")
    RequestConfig(request, paginate={"per_page": 50}).configure(table)
    c['table'] = table
    c['pagetitle'] = title
    if form: c['form'] = form
    if not c.has_key("pagedescription"): c["pagedescription"] = title
    return render_to_response(template, c, context_instance=RequestContext(request))

def all_of_a_kind_table(request, table, title, template="lists.html", intro_text=None):
    from django_tables2 import RequestConfig

    c = all_page_infos(request)
    RequestConfig(request, paginate={"per_page": 50}).configure(table)
    c['table'] = table
    c['pagetitle'] = title
    c['intro_text'] = intro_text
    c["pagedescription"] = title
    return render_to_response(template, c, context_instance=RequestContext(request))

@cache_page(3600 * 1)
def replay(request, gameID):
    c = all_page_infos(request)
    try:
        replay = Replay.objects.prefetch_related().get(gameID=gameID)
        c["replay"] = replay
    except:
        raise Http404

    allyteams = Allyteam.objects.filter(replay=replay)
    game = replay.game_release().game
    match_type = replay.match_type_short()
    c["allyteams"] = []
    for at in allyteams:
        playeraccounts = PlayerAccount.objects.filter(player__team__allyteam=at)
        teams = Team.objects.filter(allyteam=at)
        players = Player.objects.filter(account__in=playeraccounts, replay=replay).order_by("name")
        players_w_rating = list()
        old_rating = 0
        new_rating = 0
        lobby_rank_sum = 0
        if replay.notcomplete or not players.exists() or not replay.game_release().game.sldb_name or Player.objects.filter(account__accountid=0, replay=replay).exists():
            # notcomplete, no SLDB rating or bot present - no rating
            players_w_rating = [(player, None, None) for player in players]
        else:
            # TrueSkill ratings
            for pa in playeraccounts:
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

                if playeraccounts.count() > 2 or pa.sldb_privacy_mode == 0:
                    new_rating += pl_new if pl_new else 0
                    old_rating += pl_old if pl_old else 0
                else:
                    new_rating += privatize_skill(pl_new) if pl_new else 0
                    old_rating += privatize_skill(pl_old) if pl_old else 0

                if pa.sldb_privacy_mode != 0 and (not request.user.is_authenticated() or pa.accountid != request.user.get_profile().accountid):
                    if pl_new:
                        pl_new = privatize_skill(pl_new)
                    if pl_old:
                        pl_old = privatize_skill(pl_old)
                players_w_rating.append((Player.objects.get(account=pa, replay=replay), pl_old, pl_new))

        if teams:
            lobby_rank_sum = reduce(lambda x, y: x+y, [pl.rank for pl in Player.objects.filter(replay=replay, team__allyteam=at)], 0)
            c["allyteams"].append((at, players_w_rating, old_rating, new_rating, lobby_rank_sum))

    rh = list(RatingHistory.objects.filter(match=replay).values())
    for r in rh:
        playeraccount = PlayerAccount.objects.get(id=r["playeraccount_id"])
        r["num_matches"] = RatingHistory.objects.filter(game__id=r["game_id"], match_type=r["match_type"], playeraccount=playeraccount).count()
        r["playeraccount"] = playeraccount

    if replay.match_type() == "1v1":
        c["table"] = MatchRatingHistoryTable(rh)
    else:
        c["table"] = TSMatchRatingHistoryTable(rh)

    c["has_bot"] = replay.tags.filter(name="Bot").exists()
    c["specs"] = Player.objects.filter(replay=replay, spectator=True).order_by("name")
    c["upload_broken"] = UploadTmp.objects.filter(replay=replay).exists()
    c["mapoptions"] = MapOption.objects.filter(replay=replay).order_by("name")
    c["modoptions"] = ModOption.objects.filter(replay=replay).order_by("name")
    c["replay_details"] = True
    c["was_stopped"] = not allyteams.filter(winner=True).exists()
    c["is_draw"] = allyteams.filter(winner=True).count() > 1
    c["pagedescription"] = "%s %s %s match on %s (%s)"%(replay.num_players(), replay.match_type(), replay.game_release().game.name, replay.map_info.name, replay.unixTime)
    c["replay_owners"] = get_owner_list(replay.uploader)
    c["extra_media"] = ExtraReplayMedia.objects.filter(replay=replay)
    c["known_video_formats"] = ["video/webm", "video/mp4", "video/ogg", "video/x-flv", "application/ogg"]
    c["has_video"] = c["extra_media"].filter(media_magic_mime__in=c["known_video_formats"]).exists()

    return render_to_response('replay.html', c, context_instance=RequestContext(request))

def mapmodlinks(request, gameID):
    c = all_page_infos(request)

    replay = get_object_or_404(Replay, gameID=gameID)
    gamename = replay.gametype
    mapname  = replay.map_info.name

    from xmlrpclib import ServerProxy
    try:
        proxy = ServerProxy('http://api.springfiles.com/xmlrpc.php', verbose=False)

        searchstring = {"springname" : gamename.replace(" ", "*"), "category" : "game",
                        "torrent" : False, "metadata" : False, "nosensitive" : True, "images" : False}
        c['game_info'] = proxy.springfiles.search(searchstring)

        searchstring = {"springname" : mapname.replace(" ", "*"), "category" : "map",
                        "torrent" : False, "metadata" : False, "nosensitive" : True, "images" : False}
        c['map_info'] = proxy.springfiles.search(searchstring)
    except:
        c['con_error'] = "Error connecting to springfiles.com. Please retry later, or try searching yourself: <a href=\"http://springfiles.com/finder/1/%s\">game</a>  <a href=\"http://springfiles.com/finder/1/%s\">map</a>."%(gamename, mapname)

    c["pagedescription"] = "Download links for game %s and map %s."%(gamename, mapname)
    return render_to_response('mapmodlinks.html', c, context_instance=RequestContext(request))

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
                if tag.replay_count() == 1 and tag.pk > 10:
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

def autohosts(request):
    hosts = dict()
    for host in Replay.objects.values_list("autohostname", flat=True):
        if host:
            try:
                hosts[host] += 1
            except:
                hosts[host] = 0

    table = AutoHostTable([{"name": name, "count": count} for name, count in hosts.items()])
    intro_text = ["Click on a hostname to see a list of matches played on that host."]
    return all_of_a_kind_table(request, table, "List of all %d autohosts"%Map.objects.count(), intro_text=intro_text)

def autohost(request, hostname):
    replays = Replay.objects.filter(autohostname=hostname)
    return replay_table(request, replays, "%d replays on autohost '%s'"%(replays.count(), hostname))

def tags(request):
    table = TagTable([{"name": tag.name, "count": tag.replay_count()} for tag in Tag.objects.all()])
    intro_text = ["Click on a tag to see a list of matches tagged with it."]
    return all_of_a_kind_table(request, table, "List of all %d tags"%Tag.objects.count(), intro_text=intro_text)

def tag(request, reqtag):
    tag = get_object_or_404(Tag, name=reqtag)
    ext = {"adminurl": "tag", "obj": tag}

    replays = Replay.objects.filter(tags=tag)
    return replay_table(request, replays, "%d replays with tag '%s'"%(replays.count(), reqtag), ext=ext)

def maps(request):
    table = MapTable([{"name": rmap.name, "count": rmap.replay_count()} for rmap in Map.objects.all()])
    intro_text = ["Click on a map name to see a list of matches played on that map."]
    return all_of_a_kind_table(request, table, "List of all %d maps"%Map.objects.count(), intro_text=intro_text)

def rmap(request, mapname):
    rmap = get_object_or_404(Map, name=mapname)
    ext = {"adminurl": "map", "obj": rmap}

    replays = Replay.objects.filter(map_info=rmap)
    return replay_table(request, replays, "%d replays on map '%s'"%(len(replays), mapname), ext=ext)

@cache_page(3600 * 2)
def players(request):
    c = all_page_infos(request)

    c["playerlist"] = PlayerAccount.objects.order_by("preffered_name").values_list("accountid", "preffered_name")
    c["pagedescription"] = "List of all known player accounts"
    return render_to_response('all_players.html', c, context_instance=RequestContext(request))

def player(request, accountid):
    from django_tables2 import RequestConfig
    c = all_page_infos(request)

    pa = get_object_or_404(PlayerAccount, accountid=accountid)
    c['pagetitle'] = "Player "+pa.preffered_name
    c["pagedescription"] = "Statistics and match history of player %s"%pa.preffered_name
    c["playeraccount"] = pa

    c["all_names"] = pa.get_names()

    ratings = list()
    win_loss_data = list()
    if pa.accountid <=0:
        c["errmsg"] = "No rating for single player or bots."
    else:
        for game in pa.get_all_games().exclude(sldb_name=""):
            user = request.user if request.user.is_authenticated() else None
            try:
                skills = get_sldb_playerskill(game.sldb_name, [pa.accountid], user, True)[0]
            except Exception, e:
                logger.exception("Exception in get_sldb_playerskill(): %s", e)
                c["errmsg"] = "There was an error receiving the skill data. Please inform 'dansan' in the springrts forums."
            else:
                if pa != skills["account"]:
                    errmsg = "Requested (%s) and returned (%s) PlayerAccounts do not match!"%(pa, skills["account"])
                    logger.error(errmsg)
                    raise Exception(errmsg)
                if pa.sldb_privacy_mode != skills["privacyMode"]:
                    pa.sldb_privacy_mode = skills["privacyMode"]
                    pa.save()
                for mt, i in settings.SLDB_SKILL_ORDER:
                    ratings.append(Rating(game=game, match_type=mt, playeraccount=pa, trueskill_mu=skills["skills"][i][0], trueskill_sigma=skills["skills"][i][1]))
            try:
                player_stats = get_sldb_player_stats(game.sldb_name, pa.accountid)
            except Exception, e:
                logger.exception("Exception in get_sldb_player_stats(): %s", e)
                c["errmsg"] = "There was an error receiving the skill data. Please inform 'dansan' in the springrts forums."
            else:
                for match_type in ["Duel", "Team", "FFA", "TeamFFA"]:
                    total = reduce(lambda x, y: x+y, player_stats[match_type], 0)
                    if total == 0:
                        continue
                    try:
                        ratio = float(player_stats[match_type][1]*100)/float(total)
                    except ZeroDivisionError:
                        if player_stats[match_type][1] > 0:
                            ratio = 1
                        else:
                            ratio = 0
                    win_loss_data.append({"game_n_type": game.sldb_name+" "+match_type,
                                          "total"      : total,
                                          "win"        : player_stats[match_type][1],
                                          "loss"       : player_stats[match_type][0],
                                          "undecided"  : player_stats[match_type][2],
                                          "ratio"      : ratio})

    c["winlosstable"] = WinLossTable(win_loss_data, prefix="w-")
    c["playerratingtable"] = PlayerRatingTable(ratings, prefix="p-")
#     c["playerratinghistorytable"] = PlayerRatingHistoryTable(RatingHistory.objects.filter(playeraccount__in=accounts), prefix="h-")
#     RequestConfig(request, paginate={"per_page": 20}).configure(c["playerratinghistorytable"])

    replay_table_data = list()
    replays = Replay.objects.filter(player__account=pa).order_by("unixTime")
    for replay in replays:
        replay_dict = dict()
        replay_table_data.append(replay_dict)

        replay_dict["title"] = replay.title
        replay_dict["unixTime"] = replay.unixTime
        player = Player.objects.filter(replay=replay, account=pa)[0] # not using get() for the case of a spec-cheater
        replay_dict["playername"] = player.name
        try:
            replay_dict["game"] = replay.game_release().game.abbreviation
        except:
            replay_dict["game"] = replay.game_release()[:12]
        replay_dict["match_type"] = replay.match_type()
        try:
            team = Team.objects.get(replay=replay, teamleader=player)
            if team.allyteam.winner:
                replay_dict["result"] = "won"
            else:
                replay_dict["result"] = "lost"
            replay_dict["side"] = team.side
        except:
            replay_dict["result"] = "spec"
            replay_dict["side"] = "spec"
        replay_dict["gameID"] = replay.gameID
        replay_dict["accountid"] = PlayerAccount.objects.get(player=player).accountid

    c['table'] = PlayersReplayTable(replay_table_data, prefix="r-", order_by="-unixTime")
    RequestConfig(request, paginate={"per_page": 20}).configure(c["table"])

    return render_to_response("player.html", c, context_instance=RequestContext(request))

def game(request, name):
    game = get_object_or_404(Game, name=name)
    gr_list = [{'name': gr.name, 'count': Replay.objects.filter(gametype=gr.name).count()} for gr in GameRelease.objects.filter(game=game)]
    table = GameTable(gr_list)
    return all_of_a_kind_table(request, table, "List of all %d versions of game %s"%(len(gr_list), game.name))

def games(request):
    games = []
    for gt in list(set(Replay.objects.values_list('gametype', flat=True))):
        games.append({'name': gt,
                      'count': Replay.objects.filter(gametype=gt).count()})
    table = GameTable(games)
    intro_text = ["Click on a game name to see a list of matches played."]
    return all_of_a_kind_table(request, table, "List of all %d games"%len(games), intro_text=intro_text)

def gamerelease(request, gametype):
    replays = Replay.objects.filter(gametype=gametype)
    return replay_table(request, replays, "%d replays of game '%s'"%(len(replays), gametype))

@never_cache
def search(request):
    from forms import AdvSearchForm

    form_fields = ['text', 'comment', 'tag', 'player', 'spectator', 'maps', 'game', 'matchdate', 'uploaddate', 'uploader', 'autohost']
    query = {}
    ext = {}

    if request.method == 'POST':
        # did we come from the adv search page, or from a search in the top menu?
        if request.POST.has_key("search"):
            # top menu -> search everywhere
            ext["showadvsearch"] = False

            st = request.POST["search"].strip()
            if st:
                for f in form_fields:
                    if f not in ['spectator','matchdate', 'uploaddate']:
                        query[f] = st
                form = AdvSearchForm(query)
            else:
                # empty search field in top menu
                ext["showadvsearch"] = True

                query = None
                form = AdvSearchForm()
        else:
            # advSearch was used
            ext["showadvsearch"] = True

            form = AdvSearchForm(request.POST)
            if form.is_valid():
                for f in form_fields:
                    if isinstance(form.cleaned_data[f], StringTypes):
                        # strip() strings, use only non-empty ones
                        if form.cleaned_data[f].strip():
                            query[f] = form.cleaned_data[f].strip()
                    elif form.cleaned_data[f]:
                        query[f] = form.cleaned_data[f]
            else:
                query = None
    else:
        # request.method == GET (display advSearch)
        ext["showadvsearch"] = True

        query = None
        form = AdvSearchForm()

    replays = search_replays(query)
    ext["pagedescription"] = "Search replays"
    return replay_table(request, replays, "%d replays matching your search"%len(replays), "search.html", form, ext)

def search_replays(query):
    """
    I love django Q!!!
    """
    from django.db.models import Q

    if query:
        q = Q()
        multi_and = list()

        for key in query.keys():
            if   key == 'text': q &= Q(Q(title__icontains=query['text']) | Q(long_text__icontains=query['text']))
            elif key == 'comment':
                ct = ContentType.objects.get_for_model(Replay)
                comments = Comment.objects.filter(content_type=ct, comment__icontains=query['comment'])
                c_pks = [c.object_pk for c in comments]
                q &= Q(pk__in=c_pks)
            elif key == 'tag':
                q &= Q(tags__id=query['tag'][0])
                if len(query['tag']) > 1:
                    for qtag in query['tag'][1:]:
                        multi_and.append(Q(tags__id=qtag))
            elif key == 'player':
                if query.has_key('spectator'):
                    q &= Q(player__account=PlayerAccount.objects.get(id=query['player'][0]))
                    if len(query['player']) > 1:
                        for qtag in query['player'][1:]:
                            multi_and.append(Q(player__account=PlayerAccount.objects.get(id=qtag)))
                else:
                    q &= Q(player__account=PlayerAccount.objects.get(id=query['player'][0]), player__spectator=False)
                    if len(query['player']) > 1:
                        for qtag in query['player'][1:]:
                            multi_and.append(Q(player__account=PlayerAccount.objects.get(id=qtag), player__spectator=False))
            elif key == 'spectator': pass # used in key == 'player'
            elif key == 'maps': q &= Q(map_info__id__in=query['maps'])
            elif key == 'game':
                qg = Q()
                for g_id in query['game']:
                    qg |= Q(gametype__icontains=Game.objects.get(id=g_id).name)
                q &= qg
            elif key == 'matchdate':
                start_date = query['matchdate']-datetime.timedelta(1)
                end_date   = query['matchdate']+datetime.timedelta(1)
                q &= Q(unixTime__range=(start_date, end_date))
            elif key == 'uploaddate':
                start_date = query['uploaddate']-datetime.timedelta(1)
                end_date   = query['uploaddate']+datetime.timedelta(1)
                q &= Q(upload_date__range=(start_date, end_date))
            elif key == 'uploader':
                q &= Q(uploader__id__in=query['uploader'])
            elif key == 'autohost':
                try:
                    hostnames = Replay.objects.filter(id__in=query['autohost']).values_list("autohostname", flat=True)
                    logger.debug("hostnames=%s", hostnames)
                    q &= Q(autohostname__in=hostnames)
                except:
                    pass
            else:
                logger.error("Unknown query key: query[%s]=%s",key, query[key])
                raise Exception("Unknown query key: query[%s]=%s"%(key, query[key]))

        if len(q.children):
            replays = Replay.objects.filter(q).distinct()
            for and_query in multi_and:
                replays = replays.filter(and_query).distinct()
        else:
            replays = Replay.objects.none()
    else:
        # GET or empty/bad search query
        replays = Replay.objects.none()

    return replays

@cache_page(3600 / 2)
def hall_of_fame(request, abbreviation):
    from django_tables2 import RequestConfig

    c = all_page_infos(request)
    game = get_object_or_404(Game, abbreviation=abbreviation)

    if game.sldb_name != "":
        try:
            leaderboards = get_sldb_leaderboards(game)
        except Exception, e:
            logger.exception(e)
        else:
            rc = RequestConfig(request)
            c["tables"] = list()
            for leaderboard in leaderboards:
                players = SldbLeaderboardPlayer.objects.filter(leaderboard=leaderboard)
                table = HallOfFameTable(players, prefix=leaderboard.match_type+"-")
                rc.configure(table)
                c["tables"].append((leaderboard, table))

    else:
        c["errmsg"] = "No ratings available for this game."
        logger.error("%s (%s)", c["errmsg"], game)

    if abbreviation == "ZK":
        c["intro_text"] = ['<b>The official Hall of Fame of Zero-K is at <a href="http://zero-k.info/Ladders">http://zero-k.info/Ladders</a>.</b>']
    c['pagetitle'] = "Hall Of Fame ("+game.name+")"
    c["games"] = Game.objects.exclude(sldb_name="")
    c["ladders"] = [x[1] for x in RatingBase.MATCH_TYPE_CHOICES]
    c["thisgame"] = game
    return render_to_response("hall_of_fame.html", c, context_instance=RequestContext(request))
# 
#     from django_tables2 import RequestConfig
# 
#     c = all_page_infos(request)
# 
#     game = get_object_or_404(Game, abbreviation=abbreviation)
# 
#     r1v1 = collect1v1ratings(game, "1", limitresults=True)
#     c["table_1v1"]     = RatingTable(r1v1, prefix="1-")
# 
#     for mt, mtl, prefix in [("T", "table_team", "t-"), ("F", "table_ffa", "f-"), ("G", "table_teamffa", "g-")]:
#         # get ratings for top 100 players
#         rtype = Rating.objects.filter(game=game, match_type=mt, trueskill_mu__gt=25).order_by('-trueskill_mu').values()
#         if game.abbreviation == "BA": # only for BA, because ATM the other games do not have enough matches
#             # thow out players with less than x matches in this game and category
#             rtype = [rt for rt in rtype if RatingHistory.objects.filter(game=game, match_type=mt, playeraccount=PlayerAccount.objects.get(id=rt["playeraccount_id"])).count() >= settings.HALL_OF_FAME_MIN_MATCHES][:50]
#         else:
#             rtype = list(rtype)
#         # add data needed for the table
#         for rt in rtype:
#             playeraccount = PlayerAccount.objects.get(id=rt["playeraccount_id"])
#             rt["num_matches"] = RatingHistory.objects.filter(game=game, match_type=mt, playeraccount=playeraccount).count()
#             rt["playeraccount"] = playeraccount
#             rt["playername"] = playeraccount.preffered_name
#         c[mtl] = TSRatingTable(rtype, prefix=prefix)
# 
#     rc = RequestConfig(request, paginate={"per_page": 20})
#     rc.configure(c["table_1v1"])
#     rc.configure(c["table_team"])
#     rc.configure(c["table_ffa"])
#     rc.configure(c["table_teamffa"])
# 
#     c["intro_text"]    = ["Ratings are calculated separately for 1v1, Team, FFA and TeamFFA and also separately for each game. Change the diplayed game by clicking the link above this text.", "Everyone starts with Elo=1500 (k-factor=30), Glicko=1500 (RD=350) and Trueskill(mu)=25 (sigma=25/3).", "Elo and Glicko (v1) are calculated only for 1v1. Glickos rating period is not used atm."]
#     if game.abbreviation == "BA":
#         c["intro_text"].append("Only players with at least %d matches will be listed here."%settings.HALL_OF_FAME_MIN_MATCHES)
#     c['pagetitle'] = "Hall Of Fame ("+game.name+")"
#     c["games"] = [g for g in Game.objects.all() if RatingHistory.objects.filter(game=g).exists()]
#     c["thisgame"] = game
#     c["INITIAL_RATING"] = settings.INITIAL_RATING
#     c["pagedescription"] = "Hall Of Fame for "+game.name
#     return render_to_response("hall_of_fame.html", c, context_instance=RequestContext(request))

@login_required
@never_cache
def user_settings(request):
    # TODO:
    c = all_page_infos(request)
    c["pagedescription"] = "User settings"
    return render_to_response('settings.html', c, context_instance=RequestContext(request))

def users(request):
    users = [user for user in User.objects.all() if user.replays_uploaded() > 0]
    table = UserTable([{"name": user.username, "count": user.replays_uploaded(), "accountid": user.last_name} for user in users])
    intro_text = ["Click on a username to see a list of matches uploaded by that user."]
    return all_of_a_kind_table(request, table, "List of all %d uploaders"%len(users), intro_text=intro_text)

def see_user(request, accountid):
    try:
        user = User.objects.get(last_name=accountid)
    except:
        raise Http404
    replays = Replay.objects.filter(uploader=user)
    try:
        pa = PlayerAccount.objects.get(accountid=accountid)
        txt = 'to see the users player page, <a href="'+pa.get_absolute_url()+'">click here</a>'
    except:
        txt = 'the user has no player page.'
    ext = {"intro_text": ['This page shows the users UPLOADS, '+txt]}
    return replay_table(request, replays=replays, title="%d replays uploaded by '%s'"%(len(replays), user.username), ext=ext)

def match_date(request, shortdate):
    replays = Replay.objects.filter(unixTime__startswith=shortdate)
    return replay_table(request, replays, "%d replays played on '%s'"%(len(replays), shortdate))

def upload_date(request, shortdate):
    replays = Replay.objects.filter(upload_date__startswith=shortdate)
    return replay_table(request, replays, "%d replays uploaded on '%s'"%(len(replays), shortdate))

def all_comments(request):
    table = CommentTable(Comment.objects.all())
    return all_of_a_kind_table(request, table, "List of all %d comments"%Comment.objects.count())

@never_cache
def login(request):
    import django.contrib.auth
    from django.contrib.auth.forms import AuthenticationForm

    c = all_page_infos(request)
    nexturl = request.GET.get('next')
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        form.fields["password"].max_length = 4096
        if form.is_valid():
            user = form.get_user()
            django.contrib.auth.login(request, user)
            logger.info("Logged in user '%s' (%s) a.k.a '%s'", user.username, user.last_name, user.get_profile().aliases)
            # TODO: "next" is never passed...
            if nexturl:
                dest = nexturl
            else:
                dest = "/"
            return HttpResponseRedirect(dest)
        else:
            logger.info("login error: %s", form.errors)
    else:
        form = AuthenticationForm()
    c["next"] = nexturl
    c['form'] = form
    form.fields["password"].max_length = 4096
    c["pagedescription"] = "Login form"
    return render_to_response('login.html', c, context_instance=RequestContext(request))

@never_cache
def logout(request):
    import django.contrib.auth

    username = str(request.user)
    django.contrib.auth.logout(request)
    logger.info("Logged out user '%s'", username)
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
            response['Content-Disposition'] = 'attachment; filename="%s"'%media.media_basename()
            return response
        except IOError, e:
            logger.error("Cannot read media from ExtraReplayMedia(%d) of Replay(%d): media '%s'. Exception: %s" %(media.id, media.replay.id, media.media_basename(), str(e)))
            raise Http404("Error reading '%s', please contact 'Dansan' in the springrts forum."%media.media_basename())

@login_required
@never_cache
def sldb_privacy_mode(request):
    from forms import SLDBPrivacyForm
    c = all_page_infos(request)

    accountid = request.user.get_profile().accountid
    try:
        sldb_pref = get_sldb_pref(accountid, "privacyMode")
    except:
        c["current_privacy_mode"] = -1
    else:
        c["current_privacy_mode"] = int(sldb_pref["result"])
    logger.debug("current_privacy_mode: %d (user: %s)", c["current_privacy_mode"], request.user)

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
