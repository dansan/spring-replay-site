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
from forms import ManualRatingAdjustmentForm
from xmlrating import set_rating_authenticated

logger = logging.getLogger(__package__)

@cache_control(must_revalidate=True, max_age=60)
def index(request):
    c = all_page_infos(request)
    c["newest_replays"] = Replay.objects.all().order_by("-pk")[:10]
    c["news"] = NewsItem.objects.all().order_by('-pk')[:10]
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
        if replay.notcomplete or not players.exists() or replay.game_release().game.abbreviation in ["CD", "RD"] or Player.objects.filter(account__accountid=0, replay=replay).exists():
            # notcomplete or bot present - no rating
            new_rating = 0
            old_rating = 0
            for player in Player.objects.filter(account__in=playeraccounts, replay=replay):
                players_w_rating.append((player, old_rating, new_rating))
        else:
            if match_type in ["1", "O"]:
                # Elo ratings
                try:
                    new_rating = RatingHistory.objects.get(match=replay, playeraccount=playeraccounts[0], game=game, match_type=match_type).elo
                except:
                    # no rating on this replay
                    new_rating = 0
                try:
                    # find previous Elo value
                    old_rating = RatingHistory.objects.filter(playeraccount=playeraccounts[0], game=game, match_type=match_type, match__id__lt=replay.id).order_by("-id")[0].elo
                except:
                    old_rating = 1500  # 1st match in this category -> default Elo
                players_w_rating.append((players[0], old_rating, new_rating))
            else:
                # TrueSkill ratings
                old_rating = 0
                new_rating = 0
                lobby_rank_sum = 0
                for pa in playeraccounts:
                    try:
                        pl_new = RatingHistory.objects.get(match=replay, playeraccount=pa, game=game, match_type=match_type).trueskill_mu
                        new_rating += pl_new
                    except:
                        # no rating on this replay
                        pl_new = 0
                    try:
                        # find previous TS value
                        pl_old = RatingHistory.objects.filter(playeraccount=pa, game=game, match_type=match_type, match__id__lt=replay.id).order_by("-id")[0].trueskill_mu
                    except:
                        pl_old = 25  # 1st match in this category -> default TS
                    old_rating += pl_old
                    players_w_rating.append((Player.objects.get(account=pa, replay=replay), pl_old, pl_new))

        if teams:
            lobby_rank_sum = reduce(lambda x, y: x+y, [pl.rank for pl in Player.objects.filter(replay=replay, team__allyteam=at)], 0)
            c["allyteams"].append((at, players_w_rating, old_rating, new_rating, lobby_rank_sum))

    rh = list(RatingHistory.objects.filter(match=replay).values())
    for r in rh:
        playeraccount = PlayerAccount.objects.get(id=r["playeraccount_id"])
        r["num_matches"] = RatingHistory.objects.filter(game__id=r["game_id"], match_type=r["match_type"], playeraccount__in=playeraccount.get_all_accounts()).count()
        r["playeraccount"] = playeraccount
        if replay.match_type() == "1v1 BA Tourney": r["tourney"] = True

    if replay.match_type() == "1v1":
        c["table"] = MatchRatingHistoryTable(rh)
    elif replay.match_type() == "1v1 BA Tourney":
        c["table"] = TourneyMatchRatingHistoryTable(rh)
    else:
        c["table"] = TSMatchRatingHistoryTable(rh)

    c["specs"] = Player.objects.filter(replay=replay, spectator=True).order_by("name")
    c["upload_broken"] = UploadTmp.objects.filter(replay=replay).exists()
    c["mapoptions"] = MapOption.objects.filter(replay=replay).order_by("name")
    c["modoptions"] = ModOption.objects.filter(replay=replay).order_by("name")
    c["replay_details"] = True
    c["is_draw"] = not allyteams.filter(winner=True).exists()
    c["pagedescription"] = "%s %s %s match on %s (%s)"%(replay.num_players(), replay.match_type(), replay.game_release().game.name, replay.map_info.name, replay.unixTime)

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
        raise Http404

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
    filemagic = magic.from_file(path, mime=True)
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

def tags(request):
    table = TagTable([{"name": tag.name, "count": tag.replay_count()} for tag in Tag.objects.all()])
    intro_text = ["Click on a tag to see a list of matches tagged with it."]
    return all_of_a_kind_table(request, table, "List of all %d tags"%Tag.objects.count(), intro_text=intro_text)

def tag(request, reqtag):
    tag = get_object_or_404(Tag, name=reqtag)
    ext = {"adminurl": "tag", "obj": tag}

    replays = Replay.objects.filter(tags=tag)
    return replay_table(request, replays, "%d replays with tag '%s'"%(len(replays), reqtag), ext=ext)

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
    accounts = pa.get_all_accounts()

    c["accounts"] = accounts
    c["all_names"] = accounts[0].get_all_names()
    wl = win_loss_calc(accounts)
    table_data = list()
    for t in ["1v1", "Team", "FFA", "TeamFFA"]:
        wl["at_"+t.lower()]["tag"] = t
        table_data.append(wl["at_"+t.lower()])
    wl["at_all"]["tag"] = "Total"
    table_data.append(wl["at_all"])
    c["winlosstable"] = WinLossTable(table_data, prefix="w-")

    c["playerratingtable"] = PlayerRatingTable(Rating.objects.filter(playeraccount__in=accounts), prefix="p-")
    c["playerratinghistorytable"] = PlayerRatingHistoryTable(RatingHistory.objects.filter(playeraccount__in=accounts), prefix="h-")
    RequestConfig(request, paginate={"per_page": 20}).configure(c["playerratinghistorytable"])

    replay_table_data = list()
    replays = Replay.objects.filter(player__account__in=accounts).order_by("unixTime")
    for replay in replays:
        replay_dict = dict()
        replay_table_data.append(replay_dict)

        replay_dict["title"] = replay.title
        replay_dict["unixTime"] = replay.unixTime
        player = Player.objects.filter(replay=replay, account__in=accounts)[0] # not using get() for the case of a spec-cheater
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

    c['pagetitle'] = "Player "+pa.preffered_name
    c["pagedescription"] = "Statistics and match history of player %s"%pa.preffered_name
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

    form_fields = ['text', 'comment', 'tag', 'player', 'spectator', 'maps', 'game', 'matchdate', 'uploaddate', 'uploader']
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
                    q &= Q(player__account__in=PlayerAccount.objects.get(id=query['player'][0]).get_all_accounts())
                    if len(query['player']) > 1:
                        for qtag in query['player'][1:]:
                            multi_and.append(Q(player__account__in=PlayerAccount.objects.get(id=qtag).get_all_accounts()))
                else:
                    q &= Q(player__account__in=PlayerAccount.objects.get(id=query['player'][0]).get_all_accounts(), player__spectator=False)
                    if len(query['player']) > 1:
                        for qtag in query['player'][1:]:
                            multi_and.append(Q(player__account__in=PlayerAccount.objects.get(id=qtag).get_all_accounts(), player__spectator=False))
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

#@cache_page(3600 * 24)
#def win_loss_overview(request):
#    c = all_page_infos(request)
#
#    playerlist = list()
#    for pa in PlayerAccount.objects.all():
#        try:
#            name = Player.objects.filter(account=pa).values_list("name")[0][0]
#            playerlist.append((pa.accountid, name))
#        except:
#            pass
#    playerlist.sort(key=operator.itemgetter(1))
#    c["playerlist"] = playerlist
#    return render_to_response('win_loss_overview.html', c, context_instance=RequestContext(request))

def win_loss_calc(playeraccounts):
    c = dict()

    players = Player.objects.filter(account__in=playeraccounts, spectator=False)

    ats = Allyteam.objects.filter(team__player__in=players)
    at_1v1 = ats.filter(replay__tags__name="1v1")
    at_team = ats.filter(replay__tags__name="Team")
    at_ffa = ats.filter(replay__tags__name="FFA")
    at_teamffa = ats.filter(replay__tags__name="TeamFFA")

    c["at_1v1"] = {"all": at_1v1.count(), "win": at_1v1.filter(winner=True).count(), "loss": at_1v1.filter(winner=False).count()}
    try:
        c["at_1v1"]["ratio"] = "%.02f"%(float(at_1v1.filter(winner=True).count())/at_1v1.filter(winner=False).count())
    except ZeroDivisionError:
        if at_1v1.count() == 0: c["at_1v1"]["ratio"] = "0.00"
        else: c["at_1v1"]["ratio"] = "1.00"

    c["at_team"] = {"all": at_team.count(), "win": at_team.filter(winner=True).count(), "loss": at_team.filter(winner=False).count()}
    try:
        c["at_team"]["ratio"] = "%.02f"%(float(at_team.filter(winner=True).count())/at_team.filter(winner=False).count())
    except ZeroDivisionError:
        if at_team.count() == 0: c["at_team"]["ratio"] = "0.00"
        else: c["at_team"]["ratio"] = "1.00"

    c["at_ffa"] = {"all": at_ffa.count(), "win": at_ffa.filter(winner=True).count(), "loss": at_ffa.filter(winner=False).count()}
    try:
        c["at_ffa"]["ratio"] = "%.02f"%(float(at_ffa.filter(winner=True).count())/at_ffa.filter(winner=False).count())
    except ZeroDivisionError:
        if at_ffa.count() == 0: c["at_ffa"]["ratio"] = "0.00"
        else: c["at_ffa"]["ratio"] = "1.00"

    c["at_teamffa"] = {"all": at_teamffa.count(), "win": at_teamffa.filter(winner=True).count(), "loss": at_teamffa.filter(winner=False).count()}
    try:
        c["at_teamffa"]["ratio"] = "%.02f"%(float(at_teamffa.filter(winner=True).count())/at_teamffa.filter(winner=False).count())
    except ZeroDivisionError:
        if at_teamffa.count() == 0: c["at_teamffa"]["ratio"] = "0.00"
        else: c["at_teamffa"]["ratio"] = "1.00"

    c["at_all"] = {"all": ats.count(), "win": ats.filter(winner=True).count(), "loss": ats.filter(winner=False).count()}
    try:
        c["at_all"]["ratio"] = "%.02f"%(float(ats.filter(winner=True).count())/ats.filter(winner=False).count())
    except ZeroDivisionError:
        if ats.count() == 0: c["at_all"]["ratio"] = "0.00"
        else: c["at_all"]["ratio"] = "1.00"

    return c

def collect1v1ratings(game, match_type, limitresults):
    if limitresults:
        # get ratings for top 20 players for each algorithm
        r1v1 = list(Rating.objects.filter(game=game, match_type=match_type, elo__gt=1500).order_by('-elo')[:20].values())
        r1v1.extend(Rating.objects.filter(game=game, match_type=match_type, glicko__gt=1500).order_by('-glicko')[:20].values())
        r1v1.extend(Rating.objects.filter(game=game, match_type=match_type, trueskill_mu__gt=25).order_by('-trueskill_mu')[:20].values())
    else:
        r1v1 = list(Rating.objects.filter(game=game, match_type=match_type).order_by('-elo').values())
        r1v1.extend(Rating.objects.filter(game=game, match_type=match_type).order_by('-glicko').values())
        r1v1.extend(Rating.objects.filter(game=game, match_type=match_type).order_by('-trueskill_mu').values())
    if limitresults and game.abbreviation == "BA": # only for BA, because ATM the other games do not have enough matches
        # thow out duplicates and players with less than x matches in this game and category
        r1v1 = {v["playeraccount_id"]:v for v in r1v1 if RatingHistory.objects.filter(game=game, match_type=match_type, playeraccount__in=PlayerAccount.objects.get(id=v["playeraccount_id"]).get_all_accounts()).count() > settings.HALL_OF_FAME_MIN_MATCHES}.values()
    else:
        # thow out duplicates
        r1v1 = {v["playeraccount_id"]:v for v in r1v1}.values()
    # add data needed for the table
    for r1 in r1v1:
        playeraccount = PlayerAccount.objects.get(id=r1["playeraccount_id"])
        r1["num_matches"] = RatingHistory.objects.filter(game=game, match_type=match_type, playeraccount__in=playeraccount.get_all_accounts()).count()
        r1["playeraccount"] = PlayerAccount.objects.get(id=r1["playeraccount_id"])

    return r1v1

@never_cache
def ba1v1tourney(request):
    from django_tables2 import RequestConfig

    c = all_page_infos(request)

    game = get_object_or_404(Game, abbreviation="BA")
    r1v1 = collect1v1ratings(game, "O", limitresults=False)
    c["table_1v1"]     = RatingTable(r1v1, prefix="1-")
    rh = list(RatingHistory.objects.filter(match_type="O").values())
    for r in rh:
        playeraccount = PlayerAccount.objects.get(id=r["playeraccount_id"])
        r["num_matches"] = RatingHistory.objects.filter(game__id=r["game_id"], match_type=r["match_type"], playeraccount__in=playeraccount.get_all_accounts()).count()
        r["playeraccount"] = PlayerAccount.objects.get(id=r["playeraccount_id"])
        r["title"] = Replay.objects.get(id=r["match_id"]).title
        r["gameID"] =  Replay.objects.get(id=r["match_id"]).gameID
    c["table_1v1_history"]  = Tourney1v1RatingHistoryTable(rh, prefix="H-")
    c["intro_text"]    = ["TEST TEST TEST", "The ratings here are done parallel to those done my Griffith in the forum. Values are seeded from his numbers.", "EXPERIMENTAL EXPERIMENTAL EXPERIMENTAL", "Please refer to Griffith numbers, and ignore this for now!!"]
    rc = RequestConfig(request, paginate={"per_page": 20})
    rc.configure(c["table_1v1"])
    rc.configure(c["table_1v1_history"])

    c["pagedescription"] = "Balanced Annihilation 1v1 tourney ladder"
    return render_to_response('ba1v1tourney.html', c, context_instance=RequestContext(request))

@cache_page(3600 / 2)
def hall_of_fame(request, abbreviation):
    from django_tables2 import RequestConfig

    c = all_page_infos(request)

    game = get_object_or_404(Game, abbreviation=abbreviation)

    r1v1 = collect1v1ratings(game, "1", limitresults=True)
    c["table_1v1"]     = RatingTable(r1v1, prefix="1-")

    for mt, mtl, prefix in [("T", "table_team", "t-"), ("F", "table_ffa", "f-"), ("G", "table_teamffa", "g-")]:
        # get ratings for top 100 players
        rtype = Rating.objects.filter(game=game, match_type=mt, trueskill_mu__gt=25).order_by('-trueskill_mu').values()
        if game.abbreviation == "BA": # only for BA, because ATM the other games do not have enough matches
            # thow out players with less than x matches in this game and category
            rtype = [rt for rt in rtype if RatingHistory.objects.filter(game=game, match_type=mt, playeraccount__in=PlayerAccount.objects.get(id=rt["playeraccount_id"]).get_all_accounts()).count() >= settings.HALL_OF_FAME_MIN_MATCHES][:50]
        else:
            rtype = list(rtype)
        # add data needed for the table
        for rt in rtype:
            playeraccount = PlayerAccount.objects.get(id=rt["playeraccount_id"])
            rt["num_matches"] = RatingHistory.objects.filter(game=game, match_type=mt, playeraccount__in=playeraccount.get_all_accounts()).count()
            rt["playeraccount"] = playeraccount
            rt["playername"] = playeraccount.preffered_name
        c[mtl] = TSRatingTable(rtype, prefix=prefix)

    rc = RequestConfig(request, paginate={"per_page": 20})
    rc.configure(c["table_1v1"])
    rc.configure(c["table_team"])
    rc.configure(c["table_ffa"])
    rc.configure(c["table_teamffa"])

    c["intro_text"]    = ["Ratings are calculated separately for 1v1, Team, FFA and TeamFFA and also separately for each game. Change the diplayed game by clicking the link above this text.", "Everyone starts with Elo=1500 (k-factor=30), Glicko=1500 (RD=350) and Trueskill(mu)=25 (sigma=25/3).", "Elo and Glicko (v1) are calculated only for 1v1. Glickos rating period is not used atm."]
    if game.abbreviation == "BA":
        c["intro_text"].append("Only players with at least %d matches will be listed here."%settings.HALL_OF_FAME_MIN_MATCHES)
    c['pagetitle'] = "Hall Of Fame ("+game.name+")"
    c["games"] = [g for g in Game.objects.all() if RatingHistory.objects.filter(game=g).exists()]
    c["thisgame"] = game
    c["INITIAL_RATING"] = settings.INITIAL_RATING
    c["pagedescription"] = "Hall Of Fame for "+game.name
    return render_to_response("hall_of_fame.html", c, context_instance=RequestContext(request))

@never_cache
def rating_history(request):
    table = RatingHistoryTable(RatingHistory.objects.all())
    intro_text = ["Ratings are calculated separately for 1v1, Team, FFA and TeamFFA and also separately for each game.", "Everyone starts with Elo=1500 (k-factor=30), Glicko=1500 (RD=350) and Trueskill(mu)=25 (sigma=25/3).", "Elo and Glicko (v1) are calculated only for 1v1. Glickos rating period is not used atm."]
    return all_of_a_kind_table(request, table, "Rating history", template="wide_list.html", intro_text=intro_text)

@never_cache
def manual_rating_history(request):
    table = RatingAdjustmentHistoryTable(RatingAdjustmentHistory.objects.all())
    return all_of_a_kind_table(request, table, "Manual rating adjustment history")

@staff_member_required
@never_cache
def account_unification_history(request):
    table = AccountUnificationLogTable(AccountUnificationLog.objects.all())
    return all_of_a_kind_table(request, table, "Account unification history")

@staff_member_required
@never_cache
def account_unification_rating_backup(request, aulogid):
    aulog = get_object_or_404(AccountUnificationLog, id=aulogid)
    table = AccountUnificationRatingBackupTable(AccountUnificationRatingBackup.objects.filter(account_unification_log=aulog))
    return all_of_a_kind_table(request, table, "Account unification rating backup")

@staff_member_required
@never_cache
def manual_rating_adjustment(request):
    c = all_page_infos(request)
    if request.method == 'POST':
        form = ManualRatingAdjustmentForm(request.POST)
        if form.is_valid():
            logger.debug("form.cleaned_data=%s", form.cleaned_data)
            accountid     = PlayerAccount.objects.get(id=form.cleaned_data["player"]).accountid
            game          = Game.objects.get(id=int(form.cleaned_data["game"]))
            match_type    = form.cleaned_data["match_type"]
            if match_type in ["T", "F", "G"]:
                rating        = form.cleaned_data["trueskill"]
            else:
                rating        = form.cleaned_data["elo"]
            admin_account = request.user.get_profile().accountid
            set_rating_authenticated(accountid, game.abbreviation, match_type, rating, admin_account)
            return HttpResponseRedirect(reverse(manual_rating_history))
    else:
        form = ManualRatingAdjustmentForm()

    c["form"] = form
    c["pagedescription"] = "History of manual rating adjustments"
    return render_to_response("manual_rating_adjustment.html", c, context_instance=RequestContext(request))

@staff_member_required
@dajaxice_register
def mra_update_game(request, paid):
    dajax = Dajax()

    pa = get_object_or_404(PlayerAccount, id=paid)
    games = Game.objects.filter(id__in=Rating.objects.filter(playeraccount=pa).values_list("game", flat=True)).order_by("name")

    if games:
        out = ["<option value=''>Please select a game.</option>"]
        out.extend(["<option value='%d'>%s</option>"%(game.id, game.name) for game in games])
    else:
        out = ["<option value=''>NO RATINGS</option>"]

    dajax.assign('#id_game', 'innerHTML', ''.join(out))
    dajax.assign('#id_match_type', 'innerHTML', '')
    dajax.assign('#id_elo', 'value', "")
    dajax.assign('#id_glicko', 'value', "")
    dajax.assign('#id_trueskill', 'value', "")
    return dajax.json()

@staff_member_required
@dajaxice_register
def mra_update_match_type(request, paid, gameid):
    dajax = Dajax()

    pa = get_object_or_404(PlayerAccount, id=paid)
    ga = get_object_or_404(Game, id=gameid)
    ra = Rating.objects.filter(playeraccount=pa, game=ga)

    def long_type(mt):
        for mtc in Rating.MATCH_TYPE_CHOICES:
            if mtc[0] == mt:
                return mtc[1]

    out = ["<option value=''>Please select a match type.</option>"]
    out.extend(["<option value='%s'>%s</option>"%(r.match_type, long_type(r.match_type)) for r in ra])

    dajax.assign('#id_match_type', 'innerHTML', ''.join(out))
    dajax.assign('#id_elo', 'value', "")
    dajax.assign('#id_glicko', 'value', "")
    dajax.assign('#id_trueskill', 'value', "")
    return dajax.json()

@staff_member_required
@dajaxice_register
def mra_update_ratings(request, paid, gameid, matchtype):
    dajax = Dajax()

    pa   = get_object_or_404(PlayerAccount, id=paid)
    if pa.primary_account:
        pa = pa.primary_account
    game = get_object_or_404(Game, id=gameid)

    try:
        rating = Rating.objects.get(game=game, match_type=matchtype, playeraccount=pa)
        elo = rating.elo
        glicko = rating.glicko
        trueskill = rating.trueskill_mu
    except:
        elo = 0
        glicko = 0
        trueskill = 0

    if matchtype in ["T", "F", "G"]:
        dajax.assign('#id_elo', 'disabled', 'True')
        dajax.clear('#id_trueskill', 'disabled')
    else:
        dajax.clear('#id_elo', 'disabled')
        dajax.assign('#id_trueskill', 'disabled', 'True')

    dajax.assign('#id_elo', 'value', str(elo))
    dajax.assign('#id_glicko', 'value', str(glicko))
    dajax.assign('#id_trueskill', 'value', str(trueskill))
    return dajax.json()

@login_required
@never_cache
def user_settings(request):
    # TODO:
    c = all_page_infos(request)
    c["pagedescription"] = "User settings"
    return render_to_response('settings.html', c, context_instance=RequestContext(request))

def users(request):
    table = UserTable([{"name": user.username, "count": user.replays_uploaded(), "accountid": user.last_name} for user in User.objects.all()])
    intro_text = ["Click on a username to see a list of matches uploaded by that user."]
    return all_of_a_kind_table(request, table, "List of all %d uploaders"%User.objects.count(), intro_text=intro_text)

def see_user(request, accountid):
    try:
        user = User.objects.get(last_name=accountid)
    except:
        raise Http404
    replays = Replay.objects.filter(uploader=user)
    return replay_table(request, replays, "%d replays uploaded by '%s'"%(len(replays), user.username))

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
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            django.contrib.auth.login(request, user)
            logger.info("Logged in user '%s' (%s) a.k.a '%s'", user.username, user.last_name, user.get_profile().aliases)
            nexturl = request.GET.get('next')
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
    c['form'] = form
    c["pagedescription"] = "Login form"
    return render_to_response('login.html', c, context_instance=RequestContext(request))

@never_cache
def logout(request):
    import django.contrib.auth

    username = str(request.user)
    django.contrib.auth.logout(request)
    logger.info("Logged out user '%s'", username)
    return HttpResponseRedirect("/")
