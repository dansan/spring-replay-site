# This file is part of the "spring relay site / srs" program. It is published
# under the GPLv3.
#
# Copyright (C) 2016-2020 Daniel Troeder (daniel #at# admin-box #dot# com)
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import datetime
import json
import logging
from collections import OrderedDict
from functools import reduce
from operator import or_

import MySQLdb
import requests
import ujson
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Q
from django.http import HttpResponse, HttpResponseNotFound
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django_comments.models import Comment
from eztables.views import JSON_MIMETYPE, DatatablesView

from .models import (
    Game,
    GameRelease,
    Map,
    Player,
    PlayerAccount,
    PlayerStats,
    Rating,
    Replay,
    SldbLeaderboardPlayer,
    SldbPlayerTSGraphCache,
    TeamStats,
)
from .sldb import SLDBError, get_sldb_player_stats, get_sldb_playerskill

logger = logging.getLogger(__name__)


def ajax_player_lookup(request, name):
    pa = (
        PlayerAccount.objects.exclude(accountid=0)
        .filter(player__name__icontains=name)
        .distinct()
        .select_related("player__name")
        .order_by("player__name")
        .only("accountid", "player__name")
        .values("accountid", "player__name")
    )
    return HttpResponse(ujson.dumps({"player": list(pa)}))


def ajax_map_lookup(request, name):
    maps = Map.objects.filter(name__icontains=name).distinct().values("id", "name")
    return HttpResponse(ujson.dumps({"maps": list(maps)}))


def ajax_playerrating_tbl_src(request, accountid):
    empty_result = {"iTotalRecords": 0, "iTotalDisplayRecords": 0, "aaData": list()}
    try:
        sEcho = int(request.GET["sEcho"])
        empty_result["sEcho"] = sEcho
    except Exception as exc:
        logger.error("FIXME: to broad exception handling.")
        logger.exception("trouble reading 'sEcho': %s", exc)
        return HttpResponse(ujson.dumps(empty_result))
    try:
        accountid = int(accountid)
    except Exception as exc:
        logger.error("FIXME: to broad exception handling.")
        logger.exception("accountid '%s' is not an integer: %s", accountid, exc)
        return HttpResponse(ujson.dumps(empty_result))
    if accountid == 0:
        return HttpResponse(ujson.dumps(empty_result))
    try:
        pa = PlayerAccount.objects.get(accountid=accountid)
    except Exception as exc:
        logger.error("FIXME: to broad exception handling.")
        logger.exception("cannot get PlayerAccount for accountid '%d': %s", accountid, exc)
        return HttpResponse(ujson.dumps(empty_result))

    ratings = list()
    if pa.accountid > 0:
        for game in pa.get_all_games().exclude(sldb_name=""):
            if not Rating.objects.filter(game=game, playeraccount=pa).exists():
                continue
            user = request.user if request.user.is_authenticated else None
            try:
                skills = get_sldb_playerskill(game.sldb_name, [pa.accountid], user, True)[0]
            except SLDBError as exc:
                logger.error("Retrieving skill for player %s for game %s: %s", pa, game, exc)
                continue
            else:
                if pa != skills["account"]:
                    logger.error(
                        "Requested (%s) and returned (%s) PlayerAccounts do not match!",
                        pa,
                        skills["account"],
                    )
                    continue
                if skills["status"] == 0:
                    if pa.sldb_privacy_mode != skills["privacyMode"]:
                        pa.sldb_privacy_mode = skills["privacyMode"]
                        pa.save()
                    for mt, i in settings.SLDB_SKILL_ORDER:
                        ratings.append(
                            [
                                game.name,
                                Rating.objects.filter(match_type=mt).first().get_match_type_display(),
                                skills["skills"][i][0],
                            ]
                        )

    return HttpResponse(
        ujson.dumps(
            {
                "sEcho": sEcho,
                "iTotalRecords": len(ratings),
                "iTotalDisplayRecords": len(ratings),
                "aaData": ratings,
            }
        )
    )


def ajax_winloss_tbl_src(request, accountid):
    empty_result = {"iTotalRecords": 0, "iTotalDisplayRecords": 0, "aaData": list()}
    try:
        sEcho = int(request.GET["sEcho"])
        empty_result["sEcho"] = sEcho
    except Exception as exc:
        logger.error("FIXME: to broad exception handling.")
        logger.exception("trouble reading 'sEcho': %s", exc)
        return HttpResponse(ujson.dumps(empty_result))
    try:
        accountid = int(accountid)
    except ValueError as exc:
        logger.exception("accountid '%s' is not an integer: %s", accountid, exc)
        return HttpResponse(ujson.dumps(empty_result))
    if accountid == 0:
        return HttpResponse(ujson.dumps(empty_result))
    try:
        pa = PlayerAccount.objects.get(accountid=accountid)
    except ObjectDoesNotExist as exc:
        logger.error("cannot get PlayerAccount for accountid '%d': %s", accountid, exc)
        return HttpResponse(ujson.dumps(empty_result))

    win_loss_data = list()
    for game in pa.get_all_games().exclude(sldb_name=""):
        try:
            player_stats = get_sldb_player_stats(game.sldb_name, pa.accountid)
        except SLDBError as exc:
            logger.error("Retrieving stats for player %s for game %s: %s", pa, game, exc)
            continue
        else:
            for match_type in ["Duel", "Team", "FFA", "TeamFFA"]:
                total = reduce(lambda x, y: x + y, player_stats[match_type], 0)
                if total == 0:
                    continue
                try:
                    ratio = float(player_stats[match_type][1] * 100) / float(total)
                except ZeroDivisionError:
                    if player_stats[match_type][1] > 0:
                        ratio = 1
                    else:
                        ratio = 0
                win_loss_data.append(
                    [
                        game.name,
                        match_type if match_type != "Duel" else "1v1",
                        total,
                        player_stats[match_type][1],
                        player_stats[match_type][0],
                        player_stats[match_type][2],
                        "%3.0f" % ratio + " %",
                    ]
                )

    return HttpResponse(
        ujson.dumps(
            {
                "sEcho": sEcho,
                "iTotalRecords": len(win_loss_data),
                "iTotalDisplayRecords": len(win_loss_data),
                "aaData": win_loss_data,
            }
        )
    )


def ajax_playerreplays_tbl_src(request, accountid):
    empty_result = {"iTotalRecords": 0, "iTotalDisplayRecords": 0, "aaData": list()}
    params = dict()
    for k, v in request.GET.items():
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
        except Exception as exc:
            logger.error("FIXME: to broad exception handling.")
            logger.exception("trouble reading request.GET['%s']='%s', Exception: %s", k, v, exc)
            return HttpResponse(ujson.dumps(empty_result))
    empty_result["sEcho"] = params["sEcho"]
    try:
        accountid = int(accountid)
    except Exception as exc:
        logger.error("FIXME: to broad exception handling.")
        logger.exception("accountid '%s' is not an integer: %s", accountid, exc)
        return HttpResponse(ujson.dumps(empty_result))
    if accountid == 0:
        return HttpResponse(ujson.dumps(empty_result))
    try:
        pa = PlayerAccount.objects.get(accountid=accountid)
    except Exception as exc:
        logger.error("FIXME: to broad exception handling.")
        logger.exception("cannot get PlayerAccount for accountid '%d': %s", accountid, exc)
        return HttpResponse(ujson.dumps(empty_result))

    qs = Replay.objects.filter(player__account__accountid=accountid)
    if params["sSearch"]:
        qs = qs.filter(title__icontains=params["sSearch"])

    if "iSortCol_0" in params:
        if params.get("sSortDir_0", "") == "desc":
            order = "-"
        else:
            order = ""
        if params["iSortCol_0"] == 0:
            qs = qs.order_by("{}title".format(order))
        elif params["iSortCol_0"] == 1:
            qs = qs.order_by("{}unixTime".format(order))

    replays = list()
    for replay in qs[params["iDisplayStart"] : params["iDisplayStart"] + params["iDisplayLength"]]:
        try:
            replays.append(
                [
                    replay.title,
                    replay.unixTime.strftime("%Y-%m-%d %H:%M:%S"),
                    replay._playername(pa),
                    replay.game.name,
                    replay.match_type,
                    replay._result(pa),
                    replay._faction(pa),
                    replay.gameID,
                ]
            )
        except ObjectDoesNotExist:
            return HttpResponseNotFound("<h1>Player not found</h1>")
    res = {
        "sEcho": params["sEcho"],
        "iTotalRecords": Replay.objects.filter(player__account__accountid=accountid).count(),
        "iTotalDisplayRecords": qs.count(),
        "aaData": replays,
    }
    for k, v in res.items():
        if isinstance(v, bytes):
            res[k] = v.decode("utf-8")
    return HttpResponse(ujson.dumps(res))


def gamerelease_modal(request, gameid):
    c = {"gameversions": GameRelease.objects.filter(game__id=gameid).order_by("-id")}
    return render(request, "modal_gameversions.html", c)


def ratinghistorygraph_modal(request, game_abbr, accountid, match_type):
    c = {
        "game_abbr": game_abbr,
        "game_verbose": Game.objects.get(sldb_name=game_abbr).name,
        "accountid": accountid,
        "match_type": match_type,
        "match_type_verbose": SldbPlayerTSGraphCache.match_type2sldb_name[match_type],
    }
    return render(request, "modal_rating_history_graph.html", c)


def downloadlinks(gameID, category):
    c = {}
    replay = get_object_or_404(Replay, gameID=gameID)
    try:
        if category == "game":
            args = {
                "springname": replay.gametype.replace(" ", "*"),
                "category": "game",
                "nosensitive": "on",
            }
            response = requests.get("https://springfiles.springrts.com/json.php", params=args)
            c["result"] = response.json()
        elif category == "map":
            args = {
                "springname": replay.map_info.name.replace(" ", "*"),
                "category": "map",
                "nosensitive": "on",
            }
            response = requests.get("https://springfiles.springrts.com/json.php", params=args)
            c["result"] = response.json()

        elif category == "engine":
            args = {
                "version": replay.versionString.replace(" ", "*"),
            }
            response = requests.get("https://springfiles.springrts.com/json.php", params=args)
            result = OrderedDict(
                (
                    (
                        "engine_linux",
                        {
                            "label": "Linux 32 bit",
                            "icon": "ion-social-tux",
                            "mirrors": [],
                        },
                    ),
                    (
                        "engine_linux64",
                        {
                            "label": "Linux 64 bit",
                            "icon": "ion-social-tux",
                            "mirrors": [],
                        },
                    ),
                    (
                        "engine_macosx",
                        {
                            "label": "Mac OS X",
                            "icon": "ion-social-apple",
                            "mirrors": [],
                        },
                    ),
                    (
                        "engine_windows",
                        {
                            "label": "Windows 32 bit",
                            "icon": "ion-social-windows",
                            "mirrors": [],
                        },
                    ),
                    (
                        "engine_windows64",
                        {
                            "label": "Windows 64 bit",
                            "icon": "ion-social-windows",
                            "mirrors": [],
                        },
                    ),
                )
            )
            for engine_info in response.json():
                result[engine_info["category"]]["mirrors"] = engine_info["mirrors"]
            c["result"] = list(result.values())
            logger.debug("response.url=%r", response.url)
            logger.debug("c=%r", c)
        else:
            logger.error("Unknown category %r.", category)
            c["result"] = {}
    except requests.exceptions.RequestException:
        logger.exception("Error downloading map, mod or engine info.")
        gamename = replay.gametype
        mapname = replay.map_info.name
        enginename = replay.versionString.replace("maintenance", "").strip()
        c["con_error"] = (
            "Error connecting to springfiles.com. Please retry later, or try searching yourself: "
            '<a href="http://springfiles.com/finder/1/%s">game</a>  '
            '<a href="http://springfiles.com/finder/1/%s">map</a>  '
            '<a href="http://springfiles.com/finder/1/%s">engine</a>.' % (gamename, mapname, enginename)
        )
    return c


def maplinks_modal(request, gameID):
    c = downloadlinks(gameID, "map")
    return render(request, "modal_maplinks.html", c)


def modlinks_modal(request, gameID):
    c = downloadlinks(gameID, "game")
    return render(request, "modal_modlinks.html", c)


def enginelinks_modal(request, gameID):
    c = downloadlinks(gameID, "engine")
    return render(request, "modal_enginelinks.html", c)


def stats_modal(request, gameID):
    c = {}
    try:
        # player stats
        ps = PlayerStats.objects.get(replay__gameID=gameID).decompressed
        # team stats
        ts = dict(
            (_ts["stat_type"], _ts["pk"])
            for _ts in TeamStats.objects.filter(replay__gameID=gameID).values("pk", "stat_type")
        )  # evaluate filter immediately to get all TeamStats objects with one SQL query
    except (PlayerStats.DoesNotExist, TeamStats.DoesNotExist):
        c["error"] = (
            "No statistics have been found for this match. That happens when the replay file is very old, "
            "incomplete or broken."
        )
    else:
        # player stats
        stat_order = (
            "mouseClicks",
            "mousePixels",
            "keyPresses",
            "numCommands",
            "unitCommands",
        )
        c["player_stats_header"] = (
            "Player",
            "MC/min",
            "MP/min",
            "KP/min",
            "Cmd/min",
            "Units/cmd",
        )
        player_colors = dict(
            (player.name.lower(), player.team.rgbcolor)
            for player in Player.objects.filter(replay__gameID=gameID, spectator=False)
        )
        c["player_stats"] = (
            (
                player,
                player_colors.get(player.lower(), ""),
                [
                    0.0
                    if p_stats["numCommands"] == 0
                    else p_stats[s] / float(p_stats["numCommands"])
                    if s == "unitCommands"
                    else p_stats[s] / 60.0
                    for s in stat_order
                ],
            )
            for player, p_stats in ps.items()
        )
        # team stats
        # sort by stats type
        c["team_stats"] = []
        for graphid, label in TeamStats.graphid2label.items():
            try:
                c["team_stats"].append((label, ts[graphid]))
            except KeyError:
                c["error_ts"] = (
                    "No or incomplete team statistics. Autohosts don't create them. Upload your own "
                    "demofile to see them."
                )
    return render(request, "modal_stats.html", c)


def replay_filter(queryset, filter_name):
    filter_name = str(MySQLdb.escape_string(filter_name))
    filter_name_splited = filter_name.split()
    category = filter_name_splited[0]
    selected = filter_name_splited[1]
    args = filter_name_splited[2:]

    now = datetime.datetime.now(timezone.utc)
    today = datetime.datetime(year=now.year, month=now.month, day=now.day, tzinfo=timezone.utc)
    this_month_start = datetime.datetime(year=now.year, month=now.month, day=1, tzinfo=timezone.utc)
    this_month_end = datetime.datetime(
        year=now.year if now.month < 12 else now.year + 1,
        month=((now.month + 1) % 12 or 12),
        day=1,
        tzinfo=timezone.utc,
    ) - datetime.timedelta(microseconds=1)
    last_month_end = this_month_start - datetime.timedelta(microseconds=1)
    last_month_start = datetime.datetime(
        year=last_month_end.year, month=last_month_end.month, day=1, tzinfo=timezone.utc
    )
    this_year_start = datetime.datetime(year=now.year, month=1, day=1, tzinfo=timezone.utc)
    this_year_end = datetime.datetime(year=now.year + 1, month=1, day=1, tzinfo=timezone.utc) - datetime.timedelta(
        microseconds=1
    )
    last_year_end = this_year_start - datetime.timedelta(microseconds=1)
    last_year_start = datetime.datetime(year=last_year_end.year, month=1, day=1, tzinfo=timezone.utc)
    before_last_year = last_year_start - datetime.timedelta(microseconds=1)
    epoch = datetime.datetime.fromtimestamp(0, tz=timezone.utc)

    try:
        if category == "date":
            filterfnc = {
                "t_today": queryset.filter(unixTime__range=(today, today + datetime.timedelta(days=1))),
                "t_yesterday": queryset.filter(unixTime__range=(today - datetime.timedelta(days=1), today)),
                "t_this_month": queryset.filter(unixTime__range=(this_month_start, this_month_end)),
                "t_last_month": queryset.filter(unixTime__range=(last_month_start, last_month_end)),
                "t_this_year": queryset.filter(unixTime__range=(this_year_start, this_year_end)),
                "t_last_year": queryset.filter(unixTime__range=(last_year_start, last_year_end)),
                "t_ancient": queryset.filter(unixTime__range=(epoch, before_last_year)),
                "0": queryset,
            }
            if selected == "daterange":
                range_from = datetime.datetime.fromtimestamp(int(args[0]), timezone.utc)
                range_to = datetime.datetime.fromtimestamp(int(args[1]), timezone.utc)
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
                return queryset.filter(
                    gametype__in=GameRelease.objects.filter(game__id=int(selected)).values_list("name", flat=True)
                )
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
                    return queryset.filter(
                        player__account__accountid=int(selected),
                        player__spectator=False,
                    )
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
    except Exception as exc:
        logger.error("FIXME: to broad exception handling.")
        logger.debug(
            "Exception, prob from bad argument. filter_name: '%s', Exception: %s",
            filter_name,
            exc,
        )
        return queryset


class Django17DatatablesView(DatatablesView):
    """
    https://github.com/noirbizarre/django-eztables/commit/3a6b492d2ef6dd3d82727aa03c4deb7b1d1ffdea
    """

    def json_response(self, data):
        return HttpResponse(json.dumps(data, cls=DjangoJSONEncoder), content_type=JSON_MIMETYPE)


class BrowseReplaysDTView(Django17DatatablesView):
    model = Replay
    fields = (
        "title",
        "unixTime",
        "gametype",
        "download_count",
        "comment_count",
        "gameID",
        "map_info__name",
    )

    # safe GET data for use in global_search()
    def get(self, request, *args, **kwargs):
        self._GET = request.GET
        try:
            return super(Django17DatatablesView, self).get(request, *args, **kwargs)
        except AttributeError:
            return super(Django17DatatablesView, self).get(request, (), {})

    def global_search(self, queryset):
        """Filter a queryset with global search"""
        for k, v in self._GET.items():
            if k.startswith("btnfilter") and v.strip():
                queryset = replay_filter(queryset, v)
        search = self.dt_data["sSearch"]
        if search:
            search_fields = list()
            for k, v in self.dt_data.items():
                if k.startswith("bSearchable_") and v is True:
                    index = int(k.split("bSearchable_")[1])
                    search_fields.append(self.get_db_fields()[index])
            if self.dt_data["bRegex"]:
                criterions = [Q(**{"%s__iregex" % field: search}) for field in search_fields if self.can_regex(field)]
                if len(criterions) > 0:
                    search = reduce(or_, criterions)
                    queryset = queryset.filter(search)
            else:
                for term in search.split():
                    criterions = (Q(**{"%s__icontains" % field: term}) for field in search_fields)
                    search = reduce(or_, criterions)
                    queryset = queryset.filter(search)
        return queryset


def hof_tbl_src(request, leaderboardid):
    empty_result = {"iTotalRecords": 0, "iTotalDisplayRecords": 0, "aaData": list()}
    try:
        sEcho = int(request.GET["sEcho"])
        empty_result["sEcho"] = sEcho
    except Exception as exc:
        logger.error("FIXME: to broad exception handling.")
        logger.exception("trouble reading 'sEcho': %s", exc)
        return HttpResponse(ujson.dumps(empty_result))

    lps = list(
        SldbLeaderboardPlayer.objects.filter(leaderboard__id=int(leaderboardid)).values_list(
            "rank",
            "account__preffered_name",
            "trusted_skill",
            "estimated_skill",
            "uncertainty",
            "inactivity",
            "account__accountid",
        )
    )
    return HttpResponse(
        ujson.dumps(
            {
                "sEcho": sEcho,
                "iTotalRecords": len(lps),
                "iTotalDisplayRecords": len(lps),
                "aaData": lps,
            }
        )
    )


class CommentDTView(Django17DatatablesView):
    model = Comment
    fields = (
        "submit_date",
        "user_name",
        "comment",
        "user__userprofile__accountid",
        "object_pk",
    )

    def global_search(self, queryset):
        return super(CommentDTView, self).global_search(queryset.filter(is_removed=False))
