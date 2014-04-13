# This file is part of the "spring relay site / srs" program. It is published
# under the GPLv3.
#
# Copyright (C) 2012 Daniel Troeder (daniel #at# admin-box #dot# com)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

import datetime
import json
import MySQLdb
from eztables.views import DatatablesView

from django.http import HttpResponse
from django.conf import settings
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.utils import timezone
from django.contrib.comments import Comment

from srs.common import all_page_infos
from srs.models import PlayerAccount, Map, Rating, Replay, GameRelease, SldbLeaderboardPlayer
from srs.sldb import get_sldb_playerskill, get_sldb_player_stats

import logging
logger = logging.getLogger(__package__)

def ajax_player_lookup(request, name):
    pa = PlayerAccount.objects.exclude(accountid=0).filter(player__name__icontains=name).distinct().select_related("player__name").order_by('player__name').only("accountid", "player__name").values("accountid", "player__name")
    return HttpResponse(json.dumps({'player': list(pa)}))

def ajax_map_lookup(request, name):
    maps = Map.objects.filter(name__icontains=name).distinct().values("id", "name")
    return HttpResponse(json.dumps({'maps': list(maps)}))

def ajax_playerrating_tbl_src(request, accountid):
    empty_result = {"iTotalRecords": 0,
                    "iTotalDisplayRecords": 0,
                    "aaData": list()}
    try:
        sEcho = int(request.GET["sEcho"])
        empty_result["sEcho"] = sEcho
    except Exception, e:
        logger.exception("trouble reading 'sEcho': %s", e)
        return HttpResponse(json.dumps(empty_result))
    try:
        accountid = int(accountid)
    except Exception, e:
        logger.exception("accountid '%s' is not an integer: %s", accountid, e)
        return HttpResponse(json.dumps(empty_result))
    try:
        pa = PlayerAccount.objects.get(accountid=accountid)
    except Exception, e:
        logger.exception("cannot get PlayerAccount for accountid '%d': %s", accountid, e)
        return HttpResponse(json.dumps(empty_result))

    ratings = list()
    if pa.accountid > 0:
        for game in pa.get_all_games().exclude(sldb_name=""):
            if not Rating.objects.filter(game=game, playeraccount=pa).exists():
                continue
            user = request.user if request.user.is_authenticated() else None
            try:
                skills = get_sldb_playerskill(game.sldb_name, [pa.accountid], user, True)[0]
            except Exception, e:
                logger.exception("Exception in get_sldb_playerskill(): %s", e)
                continue
            else:
                if pa != skills["account"]:
                    logger.error("Requested (%s) and returned (%s) PlayerAccounts do not match!", pa, skills["account"])
                    continue
                if skills["status"] == 0:
                    if pa.sldb_privacy_mode != skills["privacyMode"]:
                        pa.sldb_privacy_mode = skills["privacyMode"]
                        pa.save()
                    for mt, i in settings.SLDB_SKILL_ORDER:
                        ratings.append([game.name,
                                        Rating.objects.filter(match_type=mt).first().get_match_type_display(),
                                        skills["skills"][i][0]])

    return HttpResponse(json.dumps({"sEcho": sEcho,
                                    "iTotalRecords": len(ratings),
                                    "iTotalDisplayRecords": len(ratings),
                                    "aaData": ratings}))

def ajax_winloss_tbl_src(request, accountid):
    empty_result = {"iTotalRecords": 0,
                    "iTotalDisplayRecords": 0,
                    "aaData": list()}
    try:
        sEcho = int(request.GET["sEcho"])
        empty_result["sEcho"] = sEcho
    except Exception, e:
        logger.exception("trouble reading 'sEcho': %s", e)
        return HttpResponse(json.dumps(empty_result))
    try:
        accountid = int(accountid)
    except Exception, e:
        logger.exception("accountid '%s' is not an integer: %s", accountid, e)
        return HttpResponse(json.dumps(empty_result))
    try:
        pa = PlayerAccount.objects.get(accountid=accountid)
    except Exception, e:
        logger.exception("cannot get PlayerAccount for accountid '%d': %s", accountid, e)
        return HttpResponse(json.dumps(empty_result))

    win_loss_data = list()
    for game in pa.get_all_games().exclude(sldb_name=""):
        try:
            player_stats = get_sldb_player_stats(game.sldb_name, pa.accountid)
        except Exception, e:
            logger.exception("Exception in get_sldb_player_stats(): %s", e)
            continue
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
                win_loss_data.append([game.name,
                                      match_type if match_type != "Duel" else "1v1",
                                      total, player_stats[match_type][1],
                                      player_stats[match_type][0],
                                      player_stats[match_type][2],
                                      '%3.0f'%ratio + " %"])

    return HttpResponse(json.dumps({"sEcho": sEcho,
                                    "iTotalRecords": len(win_loss_data),
                                    "iTotalDisplayRecords": len(win_loss_data),
                                    "aaData": win_loss_data}))

def ajax_playerreplays_tbl_src(request, accountid):
    empty_result = {"iTotalRecords": 0,
                    "iTotalDisplayRecords": 0,
                    "aaData": list()}
    params = dict()
    for k,v in request.GET.items():
        try:
            if k[0] == "i":
                params[k] = int(v)
            elif k[0] == "s" or k[0] == "m":
                params[k] = MySQLdb.escape_string(v)
            elif k[0] == "b":
                params[k] = v == "true"
            elif k[0] == "_":
                pass
            else:
                raise Exception("Unhandled parameter type")
        except Exception, e:
            logger.exception("trouble reading request.GET['%s']='%s', Exception: %s", k, v, e)
            return HttpResponse(json.dumps(empty_result))
    empty_result["sEcho"] = params["sEcho"]
    try:
        accountid = int(accountid)
    except Exception, e:
        logger.exception("accountid '%s' is not an integer: %s", accountid, e)
        return HttpResponse(json.dumps(empty_result))
    try:
        pa = PlayerAccount.objects.get(accountid=accountid)
    except Exception, e:
        logger.exception("cannot get PlayerAccount for accountid '%d': %s", accountid, e)
        return HttpResponse(json.dumps(empty_result))

    logger.debug("sEcho: %s, accountid: %d, pa: %s", params["sEcho"], accountid, pa)
    qs = Replay.objects.filter(player__account__accountid=accountid)
    logger.debug("qs 0 : %d", qs.count())
    if params["sSearch"]:
        qs = qs.filter(title__icontains=params["sSearch"])
        logger.debug("qs sSearch : %d", qs.count())

    if params.has_key("iSortCol_0"):
        if params.has_key("sSortDir_0") and params["sSortDir_0"] == "desc":
            order = "-"
        else:
            order = ""
        if params["iSortCol_0"] == 0:
            qs = qs.order_by(order + "title")
        elif params["iSortCol_0"] == 1:
            qs = qs.order_by(order + "unixTime")

    replays = list()
    for replay in qs[params["iDisplayStart"]:params["iDisplayStart"]+params["iDisplayLength"]]:
        replays.append([replay.title,
                        replay.unixTime.strftime("%Y-%m-%d %H:%M:%S"),
                        replay._playername(pa),
                        replay.game.name,
                        replay.match_type,
                        replay._result(pa),
                        replay._faction(pa),
                        replay.gameID])
    logger.debug("len(replays): %d", len(replays))
    return HttpResponse(json.dumps({"sEcho": params["sEcho"],
                                    "iTotalRecords": Replay.objects.filter(player__account__accountid=accountid).count(),
                                    "iTotalDisplayRecords": qs.count(),
                                    "aaData": replays}))

def gamerelease_modal(request, gameid):
    c = all_page_infos(request)
    c["gameversions"] = GameRelease.objects.filter(game__id=gameid).order_by("-id")
    return render_to_response('modal_gameversions.html', c, context_instance=RequestContext(request))

def mapmodlinks(gameID):
    replay = get_object_or_404(Replay, gameID=gameID)
    gamename = replay.gametype
    mapname  = replay.map_info.name
    result = dict()

    from xmlrpclib import ServerProxy
    try:
        proxy = ServerProxy('http://api.springfiles.com/xmlrpc.php', verbose=False)

        searchstring = {"springname" : gamename.replace(" ", "*"), "category" : "game",
                        "torrent" : False, "metadata" : False, "nosensitive" : True, "images" : False}
        result['game_info'] = proxy.springfiles.search(searchstring)

        searchstring = {"springname" : mapname.replace(" ", "*"), "category" : "map",
                        "torrent" : False, "metadata" : False, "nosensitive" : True, "images" : False}
        result['map_info'] = proxy.springfiles.search(searchstring)
    except:
        result['con_error'] = "Error connecting to springfiles.com. Please retry later, or try searching yourself: <a href=\"http://springfiles.com/finder/1/%s\">game</a>  <a href=\"http://springfiles.com/finder/1/%s\">map</a>."%(gamename, mapname)

    return result

def maplinks_modal(request, gameID):
    c = all_page_infos(request)

    mml = mapmodlinks(gameID)
    for k,v in mml.items():
        c[k] = v

    return render_to_response('modal_maplinks.html', c, context_instance=RequestContext(request))

def modlinks_modal(request, gameID):
    c = all_page_infos(request)

    mml = mapmodlinks(gameID)
    for k,v in mml.items():
        c[k] = v

    return render_to_response('modal_modlinks.html', c, context_instance=RequestContext(request))


def replay_filter(queryset, filter_name):
    filter_name = str(MySQLdb.escape_string(filter_name))
    filter_name_splited = filter_name.split()
    category = filter_name_splited[0]
    selected = filter_name_splited[1]
    args     = filter_name_splited[2:]

    now               = datetime.datetime.now(timezone.utc)
    today             = datetime.datetime(year=now.year, month=now.month, day=now.day, tzinfo=timezone.utc)
    this_month_start  = datetime.datetime(year=now.year, month=now.month, day=1, tzinfo=timezone.utc)
    this_month_end    = datetime.datetime(year=now.year, month=now.month+1, day=1, tzinfo=timezone.utc) - datetime.timedelta(microseconds=1)
    last_month_end    = this_month_start - datetime.timedelta(microseconds=1)
    last_month_start  = datetime.datetime(year=last_month_end.year, month=last_month_end.month, day=1, tzinfo=timezone.utc)
    this_year_start   = datetime.datetime(year=now.year, month=1, day=1, tzinfo=timezone.utc)
    this_year_end     = datetime.datetime(year=now.year+1, month=1, day=1, tzinfo=timezone.utc) - datetime.timedelta(microseconds=1)
    last_year_end     = this_year_start - datetime.timedelta(microseconds=1)
    last_year_start   = datetime.datetime(year=last_year_end.year, month=1, day=1, tzinfo=timezone.utc)
    before_last_year  = last_year_start - datetime.timedelta(microseconds=1)
    epoch             = datetime.datetime.fromtimestamp(0, tz=timezone.utc)

    try:
        if category == "date":
            filterfnc = {
                         "t_today"      : queryset.filter(unixTime__range=(today, today + datetime.timedelta(days=1))),
                         "t_yesterday"  : queryset.filter(unixTime__range=(today - datetime.timedelta(days=1), today)),
                         "t_this_month" : queryset.filter(unixTime__range=(this_month_start, this_month_end)),
                         "t_last_month" : queryset.filter(unixTime__range=(last_month_start, last_month_end)),
                         "t_this_year"  : queryset.filter(unixTime__range=(this_year_start, this_year_end)),
                         "t_last_year"  : queryset.filter(unixTime__range=(last_year_start, last_year_end)),
                         "t_ancient"    : queryset.filter(unixTime__range=(epoch, before_last_year)),
                         "0"            : queryset,
                      }
            if selected == "daterange":
                range_from = datetime.datetime.fromtimestamp(int(args[0]), timezone.utc)
                range_to   = datetime.datetime.fromtimestamp(int(args[1]), timezone.utc)
                filterfnc["daterange"] = queryset.filter(unixTime__range=(range_from, range_to))
            return filterfnc[selected]
        elif category == "map":
            if int(selected) == 0:
                return queryset
            else:
                return queryset.filter(map_info=Map.objects.get(id=int(selected)))
        elif category == "tag":
            if int(selected) == 0:
                return queryset
            else:
                return queryset.filter(tags__id=int(selected))
        elif category == "game":
            if int(selected) == 0:
                return queryset
            else:
                return queryset.filter(gametype__in=GameRelease.objects.filter(game__id=int(selected)).values_list("name", flat=True))
        elif category == "gameversion":
            if int(selected) == 0:
                return queryset
            else:
                return queryset.filter(gametype=GameRelease.objects.get(id=int(selected)).name)
        elif category == "player":
            if int(selected) == 0:
                return queryset
            else:
                if args and args[0] == "spec":
                    # include spectators
                    return queryset.filter(player__account__accountid=int(selected))
                else:
                    return queryset.filter(player__account__accountid=int(selected), player__spectator=False)
        elif category == "autohost":
            if selected == "-":
                return queryset
            else:
                return queryset.filter(autohostname=selected)
        elif category == "uploader":
            if selected == "-":
                return queryset
            else:
                return queryset.filter(uploader__username=selected)
    except Exception, e:
        logger.debug("Exception, prob from bad argument. filter_name: '%s', Exception: %s", filter_name, e)
        return queryset

class BrowseReplaysDTView(DatatablesView):
    model = Replay
    fields = ("title",
              "unixTime",
              "uploader__username",
              "download_count",
              "comment_count",
              "gameID"
              )

    def global_search(self, queryset):
        '''Filter a queryset with global search'''
        from django.db.models import Q
        from operator import or_
        for k,v in self.GET.items():
            if k.startswith("btnfilter") and v.strip():
                queryset = replay_filter(queryset, v)
        search = self.dt_data['sSearch']
        if search:
            search_fields = list()
            for k,v in self.dt_data.items():
                if k.startswith("bSearchable_") and v == True:
                    index = int(k.split("bSearchable_")[1])
                    search_fields.append(self.get_db_fields()[index])
            if self.dt_data['bRegex']:
                criterions = [
                    Q(**{'%s__iregex' % field: search})
                    for field in search_fields
                    if self.can_regex(field)
                ]
                if len(criterions) > 0:
                    search = reduce(or_, criterions)
                    queryset = queryset.filter(search)
            else:
                for term in search.split():
                    criterions = (Q(**{'%s__icontains' % field: term}) for field in search_fields)
                    search = reduce(or_, criterions)
                    queryset = queryset.filter(search)
        return queryset

def hof_tbl_src(request, leaderboardid):
    empty_result = {"iTotalRecords": 0,
                    "iTotalDisplayRecords": 0,
                    "aaData": list()}
    try:
        sEcho = int(request.GET["sEcho"])
        empty_result["sEcho"] = sEcho
    except Exception, e:
        logger.exception("trouble reading 'sEcho': %s", e)
        return HttpResponse(json.dumps(empty_result))

    lps = list(SldbLeaderboardPlayer.objects.filter(leaderboard__id=int(leaderboardid)).values_list("rank", "account__preffered_name", "trusted_skill", "estimated_skill", "uncertainty", "inactivity", "account__accountid"))
    return HttpResponse(json.dumps({"sEcho": sEcho,
                                    "iTotalRecords": len(lps),
                                    "iTotalDisplayRecords": len(lps),
                                    "aaData": lps}))

class CommentDTView(DatatablesView):
    model = Comment
    fields = ("submit_date",
              "user_name",
              "comment",
              "user__userprofile__accountid",
              "object_pk"
              )
