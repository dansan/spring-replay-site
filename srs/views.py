# This file is part of the "spring relay site / srs" program. It is published
# under the GPLv3.
#
# Copyright (C) 2012 Daniel Troeder (daniel #at# admin-box #dot# com)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.core.context_processors import csrf
from django.template import RequestContext
from django.db.models import Count
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import Http404
from django.contrib.comments import Comment
import django_tables2 as tables
from django_tables2 import RequestConfig

from tempfile import mkstemp
import os
import sets
import shutil
import functools
import locale
import datetime

import parse_demo_file
import spring_maps
from models import *
from forms import UploadFileForm

def all_page_infos(request):
    c = {}
    c.update(csrf(request))
    c["total_replays"]   = Replay.objects.count()
    c["top_tags"]        = Tag.objects.annotate(num_replay=Count('replay')).order_by('-num_replay')[:20]
    c["top_maps"]        = Map.objects.annotate(num_replay=Count('replay')).order_by('-num_replay')[:20]
    c["top_players"]     = [Player.objects.filter(account=pa)[0] for pa in PlayerAccount.objects.exclude(accountid=9999999999).annotate(num_replay=Count('player__replay')).order_by('-num_replay')[:20]]
    c["latest_comments"] = Comment.objects.reverse()[:5]
    return c

def index(request):
    c = all_page_infos(request)
    c["newest_replays"] = []
    for replay in Replay.objects.all().order_by('-pk')[:10]:
        c["newest_replays"].append((replay, ReplayFile.objects.get(replay=replay).download_count))
    c["news"] = NewsItem.objects.all().order_by('-pk')[:10]
    return render_to_response('index.html', c, context_instance=RequestContext(request))

@login_required
def upload(request):
    c = all_page_infos(request)
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            ufile = request.FILES['file']
            short = request.POST['short']
            long_text = request.POST['long_text']
            tags = request.POST['tags']
            (path, written_bytes) = save_uploaded_file(ufile)
#            try:
            if written_bytes != ufile.size:
                return HttpResponse("Could not store the replay file. Please contact the administrator.")

            demofile = parse_demo_file.Parse_demo_file(path)
            demofile.check_magic()
            demofile.parse()

            try:
                replay = Replay.objects.get(gameID=demofile.header["gameID"])
                return HttpResponse('Uploaded replay already exists: <a href="/replay/%s/">%s</a>'%(replay.gameID, replay.__unicode__()))
            except:
                shutil.move(path, settings.MEDIA_ROOT)
                replay = store_demofile_data(demofile, tags, settings.MEDIA_ROOT+os.path.basename(path), file.name, short, long_text, request.user)
            return HttpResponseRedirect("/replay/%s/"%replay.gameID)
#            except Exception, e:
#                return HttpResponse("The was a problem with the upload: %s<br/>Please retry or contact the administrator.<br/><br/><a href="/">Home</a>"%e)
    else:
        form = UploadFileForm()
    c['form'] = form
    return render_to_response('upload.html', c, context_instance=RequestContext(request))

class ReplayTable(tables.Table):
    title          = tables.Column()
    upload_date    = tables.Column()
    uploader       = tables.Column()
#    download_count = tables.Column()
#    comment_count  = tables.Column()
    class Meta:
        attrs    = {'class': 'paleblue'}
        order_by = "-upload_date"

def replays(request):
    c = all_page_infos(request)
    all_replays = Replay.objects.all().order_by("unixTime")
    table = ReplayTable(all_replays)
    RequestConfig(request, paginate={"per_page": 50}).configure(table)
    c['table'] = table
    return render_to_response('replays.html', c, context_instance=RequestContext(request))

def replay(request, gameID):
    # TODO
    c = all_page_infos(request)
#    return HttpResponse('<b>TODO</b><br/><br/>You are looking at replay %s:<br/>%s<br/><a href="/download/%s/">Download</a><br/><br/><a href="/">Home</a>' % (gameID, Replay.objects.get(gameID=gameID).__unicode__(), gameID))
    try:
        c["replay"] = Replay.objects.prefetch_related().get(gameID=gameID)
    except:
        # TODO: nicer error handling
        raise Http404

    c["allyteams"] = []
    for at in Allyteam.objects.filter(replay=c["replay"]):
        teams = Team.objects.prefetch_related("teamleader").filter(allyteam=at, replay=c["replay"])
        if teams:
            c["allyteams"].append((at, teams))
    c["specs"] = Player.objects.filter(replay=c["replay"], spectator=True)

    return render_to_response('replay.html', c, context_instance=RequestContext(request))


def download(request, gameID):
    # TODO
    c = all_page_infos(request)
    try:
        rf = ReplayFile.objects.get(replay__gameID=gameID)
    except:
        # TODO: nicer error handling
        raise Http404

    rf.download_count += 1
    rf.save()
    return HttpResponseRedirect(settings.STATIC_URL+"replays/"+rf.filename)

def tags(request):
    # TODO
    c = all_page_infos(request)
    rep = "<b>TODO</b><br/><br/>list of all %d tags:<br/>"%Tag.objects.count()
    for tag in Tag.objects.all().order_by("name"):
        rep += '* <a href="/tag/%s/">%s</a><br/>'%(tag.__unicode__(), tag.__unicode__())
    rep += '<br/><br/><a href="/">Home</a>'
    return HttpResponse(rep)

def tag(request, reqtag):
    # TODO
    c = all_page_infos(request)
    rep = "<b>TODO</b><br/><br/>list of games with tag '%s':<br/>"%reqtag
    for replay in Replay.objects.filter(tags__name=reqtag):
        rep += '* <a href="/replay/%s/">%s</a><br/>'%(replay.gameID, replay.__unicode__())
    rep += '<br/><br/><a href="/">Home</a>'
    return HttpResponse(rep)

def maps(request):
    # TODO
    c = all_page_infos(request)
    rep = "<b>TODO</b><br/><br/>list of all %d maps:<br/>"%Map.objects.count()
    for smap in Map.objects.all().order_by("name"):
        rep += '* <a href="/map/%s/">%s</a><br/>'%(smap.__unicode__(), smap.__unicode__())
    rep += '<br/><br/><a href="/">Home</a>'
    return HttpResponse(rep)

def rmap(request, mapname):
    # TODO
    c = all_page_infos(request)
    rep = "<b>TODO</b><br/><br/>list of games on map '%s':<br/>"%mapname
    for replay in Replay.objects.filter(map_info__name=mapname):
        rep += '* <a href="/replay/%s/">%s</a><br/>'%(replay.gameID, replay.__unicode__())
    rep += '<br/><br/><a href="/">Home</a>'
    return HttpResponse(rep)

def players(request):
    # TODO
    c = all_page_infos(request)
    rep = "<b>TODO</b><br/><br/>list of all %d players:<br/>"%Player.objects.count()
    names = []
    for pa in PlayerAccount.objects.exclude(accountid=9999999999):
        names.extend([(name, pa.accountid) for name in pa.names.split(";")])
    names.sort(cmp=lambda x,y: cmp(x[0], y[0]))
    for name, plid in names:
        rep += '* <a href="/player/%s/">%s</a><br/>'%(plid, name)
    rep += '<br/><br/><a href="/">Home</a>'
    return HttpResponse(rep)

def player(request, accountid):
    # TODO
    c = all_page_infos(request)
    rep = "<b>TODO</b><br/><br/>This player is know as:<br/>"
    accounts = []

    try:
        accounts.append(PlayerAccount.objects.get(accountid=accountid))
    except:
        # TODO: nicer error handling
        raise Http404
    accounts.extend(PlayerAccount.objects.filter(aka=accounts[0]))
    for account in accounts:
        for a in account.names.split(";"):
            rep += '* %s<br/>'%a

    players = Player.objects.select_related("replay").filter(account__in=accounts)
    rep += "<br/><br/>This player (with one of his accounts/aliases) has played in these games:<br/>"
    for player in players:
        rep += '* <a href="/replay/%s/">%s</a><br/>'%(player.replay.gameID, player.replay.__unicode__())
    rep += '<br/><br/><a href="/">Home</a>'
    return HttpResponse(rep)

def games(request):
    # TODO
    c = all_page_infos(request)
    locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
    games = sorted(sets.Set([r.gametype for r in Replay.objects.all()]), key=functools.cmp_to_key(locale.strcoll))
    rep = "<b>TODO</b><br/><br/>list of all %d games:<br/>"%len(games)
    for game in games:
        rep += '* <a href="/game/%s/">%s</a><br/>'%(game, game)
    rep += '<br/><br/><a href="/">Home</a>'
    return HttpResponse(rep)

def game(request, gametype):
    # TODO
    c = all_page_infos(request)
    rep = "<b>TODO</b><br/><br/>list of replays of game %s:<br/>"%gametype
    for replay in Replay.objects.filter(gametype=gametype):
        rep += '* <a href="/replay/%s/">%s</a><br/>'%(replay.gameID, replay.__unicode__())
    rep += '<br/><br/><a href="/">Home</a>'
    return HttpResponse(rep)

def search(request):
    # TODO
    c = all_page_infos(request)
    resp = "<b>TODO</b><br/><br/>"
    if request.method == 'POST':
        st = request.POST["search"].strip()
        if st:
            users = User.objects.filter(username__icontains=st)
            replays = Replay.objects.filter(Q(gametype__icontains=st)|
                                            Q(title__icontains=st)|
                                            Q(short_text__icontains=st)|
                                            Q(long_text__icontains=st)|
                                            Q(rmap__name__icontains=st)|
                                            Q(tags__name__icontains=st)|
                                            Q(uploader__in=users)|
                                            Q(player__account__names__icontains=st)).distinct()

            resp += 'Your search for "%s" yielded %d results:<br/><br/>'%(st, replays.count())
            for replay in replays:
                resp += '* <a href="/replay/%s/">%s</a><br/>'%(replay.gameID, replay.__unicode__())
        else:
            HttpResponseRedirect("/search/")
    return HttpResponse(resp)

def user_settings(request):
    # TODO:
    c = all_page_infos(request)
    return render_to_response('settings.html', c, context_instance=RequestContext(request))

def users(request):
    # TODO:
    locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
    users = sorted(sets.Set([u.username for u in User.objects.all()]), key=functools.cmp_to_key(locale.strcoll))
    rep = "<b>TODO</b><br/><br/>list of all %d users:<br/>"%len(users)
    for user in users:
        rep += '* <a href="/user/%s/">%s</a><br/>'%(user, user)
    rep += '<br/><br/><a href="/">Home</a>'
    return HttpResponse(rep)

def see_user(request, username):
    # TODO:
    rep = "<b>TODO</b><br/><br/>"
    user = User.objects.get(username=username)
    try:
        rep += "list of replays uploaded by %s:<br/>"%username
        for replay in Replay.objects.filter(uploader=user):
            rep += '* <a href="/replay/%s/">%s</a><br/>'%(replay.gameID, replay.__unicode__())
    except:
        rep += "user %s unknown.<br/>"%username
    rep += '<br/><br/><a href="/">Home</a>'
    return HttpResponse(rep)

def match_date(request, shortdate):
    # TODO:
    rep = "<b>TODO</b><br/><br/>"
    rep += "list of replays played on %s:<br/>"%shortdate
    for replay in Replay.objects.filter(unixTime__startswith=shortdate):
        rep += '* <a href="/replay/%s/">%s</a><br/>'%(replay.gameID, replay.__unicode__())
    rep += '<br/><br/><a href="/">Home</a>'
    return HttpResponse(rep)

def upload_date(request, shortdate):
    # TODO:
    rep = "<b>TODO</b><br/><br/>"
    rep += "list of replays uploaded on %s:<br/>"%shortdate
    for replay in Replay.objects.filter(upload_date__startswith=shortdate):
        rep += '* <a href="/replay/%s/">%s</a><br/>'%(replay.gameID, replay.__unicode__())
    rep += '<br/><br/><a href="/">Home</a>'
    return HttpResponse(rep)

def all_comments(request):
    # TODO:
    all_c = Comment.objects.all()
    rep = "<b>TODO</b><br/><br/>"
    rep += "list of all %d comments:<br/>"%all_c.count()
    for c in all_c:
        rep += '* User <a href="/user/%s/">%s</a> commented on <a href="/replay/%s/">replay %s</a>: %s <a href="%s">more...</a><br/>'%(c.user_name, c.user_name, c.content_object.gameID, c.content_object.__unicode__(), c.comment[:20], c.get_absolute_url())
    rep += '<br/><br/><a href="/">Home</a>'
    return HttpResponse(rep)

###############################################################################
###############################################################################

def save_uploaded_file(ufile):
    """
    may raise an exception from os.open/write/close()
    """
    (fd, path) = mkstemp(suffix=".sdf", prefix=ufile.name[:-4]+"__")
    written_bytes = 0
    for chunk in ufile.chunks():
        written_bytes += os.write(fd, chunk)
    os.close(fd)
    return (path, written_bytes)

def store_demofile_data(demofile, tags, path, filename, short, long_text, user):
    """
    Store all data about this replay in the database
    """
    replay = Replay()
    replay.uploader = user

    # copy match infos 
    for key in ["versionString", "gameID", "wallclockTime"]:
        replay.__setattr__(key, demofile.header[key])
    replay.unixTime = datetime.datetime.strptime(demofile.header["unixTime"], "%Y-%m-%d %H:%M:%S")
    for key in ["mapname", "autohostname", "gametype", "startpostype"]:
        if demofile.game_setup["host"].has_key(key):
            replay.__setattr__(key, demofile.game_setup["host"][key])

    replay.save()

    # save AllyTeams
    allyteams = {}
    for num,val in demofile.game_setup['allyteam'].items():
        allyteam = Allyteam()
        allyteams[num] = allyteam
        for k,v in val.items():
            allyteam.__setattr__(k, v)
        allyteam.replay = replay
        allyteam.winner = int(num) in demofile.winningAllyTeams
        allyteam.save()

    # winner known?
    replay.notcomplete = demofile.header['winningAllyTeamsSize'] == 0

    # get / create map infos
    try:
        replay.map_info = Map.objects.get(name=demofile.game_setup["host"]["mapname"])
    except:
        # 1st time upload for this map: fetch info and full map, create thumb
        # for index page
        smap = spring_maps.Spring_maps(demofile.game_setup["host"]["mapname"])
        smap.fetch_info()
        startpos = ""
        for coord in smap.map_info[0]["metadata"]["StartPos"]:
            startpos += "%f,%f|"%(coord["x"], coord["z"])
        startpos = startpos[:-1]
        replay.map_info = Map.objects.create(name=demofile.game_setup["host"]["mapname"], startpos=startpos, height=smap.map_info[0]["metadata"]["Height"], width=smap.map_info[0]["metadata"]["Width"])

        full_img = smap.fetch_img()
        MapImg.objects.create(filename=full_img, startpostype=-1, map_info=replay.map_info)
        smap.make_home_thumb()

    # get / create map thumbs
    if demofile.game_setup["host"]["startpostype"] == 1:
        # fixed start positions before game
        try:
            replay.map_img = MapImg.objects.get(map_info = replay.map_info, startpostype=1)
        except:
            mapfile = spring_maps.create_map_with_positions(replay.map_info)
            replay.map_img = MapImg.objects.create(filename=mapfile, startpostype=1, map_info=replay.map_info)
    elif demofile.game_setup["host"]["startpostype"] == 2:
        # start boxes
        mapfile = spring_maps.create_map_with_boxes(replay)
        replay.map_img = MapImg.objects.create(filename=mapfile, startpostype=2, map_info=replay.map_info)
    else:
        #TODO:
        raise Exception("not yet implemented")

    replay.save()

    # save tags
    if tags:
        # strip comma separated tags and remove empty ones
        tags_ = [t.strip() for t in tags.split(",") if t]
        for tag in tags_:
            t_obj, _ = Tag.objects.get_or_create(name__iexact = tag, defaults={'name': tag})
            replay.tags.add(t_obj)
    replay.save()

    # the replay file
    ReplayFile.objects.create(filename=os.path.basename(path), path=os.path.dirname(path), ori_filename=filename, download_count=0, replay=replay)

    # save map and mod options
    for k,v in demofile.game_setup['mapoptions'].items():
        MapOption.objects.create(name=k, value=v, replay=replay)

    for k,v in demofile.game_setup['modoptions'].items():
        ModOption.objects.create(name=k, value=v, replay=replay)

    # save players and their accounts
    players = {}
    for k,v in demofile.game_setup['player'].items():
        if not v.has_key("accountid"):
            # single player
            v["accountid"] = 9999999999
        if v.has_key("lobbyid"):
            # game was on springie
            v["accountid"] = v["lobbyid"]
        pa, created = PlayerAccount.objects.get_or_create(accountid=v["accountid"], defaults={'accountid': v["accountid"], 'countrycode': v["countrycode"], 'names': v["name"]})
        players[k] = Player.objects.create(account=pa, name=v["name"], rank=v["rank"], spectator=bool(v["spectator"]), replay=replay)
        if not created:
            if v["name"] not in pa.names.split(";"):
                pa.names += ";"+v["name"]
                pa.save()

    # save teams
    for num,val in demofile.game_setup['team'].items():
        team = Team()
        try:
            players[num].team = team
            players[num].save()
        except KeyError:
            # team has no player -> SP bot
            pass
        for k,v in val.items():
            if k == "allyteam":
                team.allyteam = allyteams[str(v)]
            elif k == "teamleader":
                team.teamleader = players[str(v)]
            elif k =="rgbcolor":
                team.rgbcolor = floats2rgbhex(v)
            else:
                team.__setattr__(k, v)
        team.replay = replay
        team.save()

    # work around Zero-Ks usage of useless AllyTeams
    Allyteam.objects.filter(replay=replay, team__isnull=True).delete()

    # auto add tag 1v1 2v2 etc.
    autotag = ""
    if Allyteam.objects.filter(replay=replay).count() > 3:
        autotag = "FFA"
    else:
        for at in Allyteam.objects.filter(replay=replay):
            autotag += str(Team.objects.filter(allyteam=at).count())+"v"
        autotag = autotag[:-1]

    tag, created = Tag.objects.get_or_create(name = autotag, defaults={'name': autotag})
    if created:
        replay.tags.add(tag)
    else:
        if not replay.tags.filter(name=autotag).exists():
            replay.tags.add(tag)


    # TODO: SP and bot detection

    # save descriptions
    replay.short_text = short
    replay.long_text = long_text
    replay.title = autotag+" "+short
    replay.save()

    return replay

def clamp(val, low, high):
    return min(high, max(low, val))

def floats2rgbhex(floats):
    rgb = ""
    for color in floats.split():
        rgb += str(hex(clamp(int(float(color)*256), 0, 256))[2:])
    return rgb
