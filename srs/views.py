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

import logging
from types import StringTypes
import datetime
import gzip
import magic

from models import *
from common import all_page_infos
from tables import *
from upload import save_tags, set_autotag, save_desc

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
    return replay_table(request, replays, "all %d replays"%replays.count())

def replay_table(request, replays, title, template="lists.html", form=None, ext=None, order_by=None):
    from django_tables2 import RequestConfig

    c = all_page_infos(request)
    if ext:
        for k,v in ext.items():
            c[k] = v
    if order_by:
        table = ReplayTable(replays, prefix="r-", order_by=order_by)
    else:
        table = ReplayTable(replays, prefix="r-")
    RequestConfig(request, paginate={"per_page": 50}).configure(table)
    c['table'] = table
    c['pagetitle'] = title
    if form: c['form'] = form
    return render_to_response(template, c, context_instance=RequestContext(request))

def all_of_a_kind_table(request, table, title, template="lists.html", intro_text=None):
    from django_tables2 import RequestConfig

    c = all_page_infos(request)
    RequestConfig(request, paginate={"per_page": 50}).configure(table)
    c['table'] = table
    c['pagetitle'] = title
    c['intro_text'] = intro_text
    return render_to_response(template, c, context_instance=RequestContext(request))

@cache_page(3600 * 1)
def replay(request, gameID):
    c = all_page_infos(request)
    try:
        c["replay"] = Replay.objects.prefetch_related().get(gameID=gameID)
    except:
        raise Http404

    c["allyteams"] = []
    for at in Allyteam.objects.filter(replay=c["replay"]):
        teams = Team.objects.filter(allyteam=at, replay=c["replay"])
        players = Player.objects.filter(team__in=teams).order_by("name")
        if teams:
            c["allyteams"].append((at, players))

    rh = list(RatingHistory.objects.filter(match=c["replay"]).values())
    for r in rh:
        playeraccount = PlayerAccount.objects.get(id=r["playeraccount_id"])
        r["num_matches"] = RatingHistory.objects.filter(game__id=r["game_id"], match_type=r["match_type"], playeraccount__in=playeraccount.get_all_accounts()).count()
        r["playeraccount"] = PlayerAccount.objects.get(id=r["playeraccount_id"])
        if c["replay"].match_type() == "1v1 BA Tourney": r["tourney"] = True

    if c["replay"].match_type() == "1v1":
        c["table"] = MatchRatingHistoryTable(rh)
    elif c["replay"].match_type() == "1v1 BA Tourney":
        c["table"] = TourneyMatchRatingHistoryTable(rh)
    else:
        c["table"] = TSMatchRatingHistoryTable(rh)

    c["specs"] = Player.objects.filter(replay=c["replay"], spectator=True).order_by("name")
    c["upload_broken"] = UploadTmp.objects.filter(replay=c["replay"]).exists()
    c["mapoptions"] = MapOption.objects.filter(replay=c["replay"]).order_by("name")
    c["modoptions"] = ModOption.objects.filter(replay=c["replay"]).order_by("name")
    c["replay_details"] = True

    return render_to_response('replay.html', c, context_instance=RequestContext(request))

def mapmodlinks(request, gameID):
    c = all_page_infos(request)
    try:
        replay = Replay.objects.get(gameID=gameID)
    except:
        raise Http404

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
                if tag.replays() == 1 and tag.pk > 10:
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
    try:
        rf = Replay.objects.get(gameID=gameID).replayfile
    except:
        raise Http404

    rf.download_count += 1
    rf.save()

    path = rf.path+"/"+rf.filename
    filemagic = magic.from_file(path, mime=True)
    if filemagic.endswith("gzip"):
        demofile = gzip.open(path, 'rb')
    else:
        demofile = open(path, "rb")
    if rf.filename.endswith(".gz"):
        filename = rf.filename[:-3]
    else:
        filename = rf.filename

    response = HttpResponse(demofile.read(), content_type='application/x-spring-demo')
    response['Content-Disposition'] = 'attachment; filename="%s"'%filename
    return response

def tags(request):
    table = TagTable(Tag.objects.all())
    return all_of_a_kind_table(request, table, "List of all %d tags"%Tag.objects.count())

def tag(request, reqtag):
    tag = get_object_or_404(Tag, name=reqtag)
    ext = {"adminurl": "tag", "obj": tag}

    replays = Replay.objects.filter(tags__name=reqtag)
    return replay_table(request, replays, "%d replays with tag '%s'"%(replays.count(), reqtag), ext=ext)

def maps(request):
    table = MapTable(Map.objects.all())
    return all_of_a_kind_table(request, table, "List of all %d maps"%Map.objects.count())

def rmap(request, mapname):
    rmap = get_object_or_404(Map, name=mapname)
    ext = {"adminurl": "map", "obj": rmap}
    replays = Replay.objects.filter(map_info=rmap)
    return replay_table(request, replays, "%d replays on map '%s'"%(replays.count(), mapname), ext=ext)

def players(request):
    players = []
    for pa in PlayerAccount.objects.all():
        players.append({'name': pa.preffered_name,
                        'replay_count': pa.replay_count(),
                        'spectator_count': pa.spectator_count(),
                        'accid': pa.accountid})
    table = PlayerTable(players)
    return all_of_a_kind_table(request, table, "List of all %d players"%len(players))

def player(request, accountid):
    from django_tables2 import RequestConfig
    c = all_page_infos(request)

    try:
        pa = PlayerAccount.objects.get(accountid=accountid)
        accounts = pa.get_all_accounts()
    except:
        raise Http404

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
    return render_to_response("player.html", c, context_instance=RequestContext(request))

#class PlayersReplayTable(tables.Table):
#    title          = tables.LinkColumn('replay_detail', args=[A('gameID')])
#    unixTime       = tables.Column(verbose_name="Date")
#    playername     = tables.LinkColumn('player_detail', args=[A('playeraccount.accountid')])
#    game           = tables.Column(accessor=A("game.abbreviation"), verbose_name="Game")
#    match_type     = tables.LinkColumn('replay_detail', args=[A('match.gameID')])
#    result         = tables.Column()
#    side           = tables.Column()

def game(request, name):
    game = get_object_or_404(Game, name=name)
    gr_list = [{'name': gr.name, 'replays': Replay.objects.filter(gametype=gr.name).count()} for gr in GameRelease.objects.filter(game=game)]
    table = GameTable(gr_list)
    return all_of_a_kind_table(request, table, "List of all %d versions of game %s"%(len(gr_list), game.name))

def games(request):
    games = []
    for gt in list(set(Replay.objects.values_list('gametype', flat=True))):
        games.append({'name': gt,
                      'replays': Replay.objects.filter(gametype=gt).count()})
    table = GameTable(games)
    return all_of_a_kind_table(request, table, "List of all %d games"%len(games))

def gamerelease(request, gametype):
    replays = Replay.objects.filter(gametype=gametype)
    return replay_table(request, replays, "%d replays of game '%s'"%(replays.count(), gametype))

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

    return replay_table(request, replays, "%d replays matching your search"%replays.count(), "search.html", form, ext)

def search_replays(query):
    """
    I love django Q!!!
    """
    from django.db.models import Q

    if query:
        q = Q()

        for key in query.keys():
            if   key == 'text': q |= Q(title__icontains=query['text']) | Q(long_text__icontains=query['text'])
            elif key == 'comment':
                ct = ContentType.objects.get_for_model(Replay)
                comments = Comment.objects.filter(content_type=ct, comment__icontains=query['comment'])
                c_pks = [c.object_pk for c in comments]
                q |= Q(pk__in=c_pks)
            elif key == 'tag': q |= Q(tags__name__icontains=query['tag'])
            elif key == 'player':
                if query.has_key('spectator'):
                    q |= Q(player__account__preffered_name__icontains=query['player'])
                else:
                    q |= Q(player__account__preffered_name__icontains=query['player'], player__spectator=False)
            elif key == 'spectator': pass # used in key == 'player'
            elif key == 'maps': q |= Q(map_info__name__icontains=query['maps'])
            elif key == 'game': q |= Q(gametype__icontains=query['game'])
            elif key == 'matchdate':
                start_date = query['matchdate']-datetime.timedelta(1)
                end_date   = query['matchdate']+datetime.timedelta(1)
                q |= Q(unixTime__range=(start_date, end_date))
            elif key == 'uploaddate':
                start_date = query['uploaddate']-datetime.timedelta(1)
                end_date   = query['uploaddate']+datetime.timedelta(1)
                q |= Q(upload_date__range=(start_date, end_date))
            elif key == 'uploader':
                users = User.objects.filter(username__icontains=query['uploader'])
                q |= Q(uploader__in=users)
            else:
                logger.error("Unknown query key: query[%s]=%s",key, query[key])
                raise Exception("Unknown query key: query[%s]=%s"%(key, query[key]))

        if len(q.children):
            replays = Replay.objects.filter(q).distinct()
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

    return render_to_response("hall_of_fame.html", c, context_instance=RequestContext(request))

@never_cache
def rating_history(request):
    table = RatingHistoryTable(RatingHistory.objects.all())
    intro_text = ["Ratings are calculated separately for 1v1, Team, FFA and TeamFFA and also separately for each game.", "Everyone starts with Elo=1500 (k-factor=30), Glicko=1500 (RD=350) and Trueskill(mu)=25 (sigma=25/3).", "Elo and Glicko (v1) are calculated only for 1v1. Glickos rating period is not used atm."]
    return all_of_a_kind_table(request, table, "Rating history", template="wide_list.html", intro_text=intro_text)

@login_required
@never_cache
def user_settings(request):
    # TODO:
    c = all_page_infos(request)
    return render_to_response('settings.html', c, context_instance=RequestContext(request))

def users(request):
    table = UserTable(User.objects.all())
    return all_of_a_kind_table(request, table, "List of all %d uploaders"%User.objects.count())

def see_user(request, username):
    try:
        user = User.objects.get(username=username)
    except:
        raise Http404
    replays = Replay.objects.filter(uploader=user)
    return replay_table(request, replays, "%d replays uploaded by '%s'"%(replays.count(), user))

def match_date(request, shortdate):
    replays = Replay.objects.filter(unixTime__startswith=shortdate)
    return replay_table(request, replays, "%d replays played on '%s'"%(replays.count(), shortdate))

def upload_date(request, shortdate):
    replays = Replay.objects.filter(upload_date__startswith=shortdate)
    return replay_table(request, replays, "%d replays uploaded on '%s'"%(replays.count(), shortdate))

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
            user = django.contrib.auth.authenticate(username=form.cleaned_data["username"], password=form.cleaned_data["password"])
            if user is not None:
                if user.is_active:
                    django.contrib.auth.login(request, user)
                    logger.info("Logged in user '%s'", request.user)
                    nexturl = request.GET.get('next')
                    # TODO: "next" is never passed...
                    if nexturl:
                        dest = nexturl
                    else:
                        dest = "/"
                    return HttpResponseRedirect(dest)
    else:
        form = AuthenticationForm()
    c['form'] = form
    return render_to_response('login.html', c, context_instance=RequestContext(request))

@never_cache
def logout(request):
    import django.contrib.auth

    username = str(request.user)
    django.contrib.auth.logout(request)
    logger.info("Logged out user '%s'", username)
    return HttpResponseRedirect("/")
