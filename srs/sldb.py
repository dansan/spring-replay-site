# This file is part of the "spring relay site / srs" program. It is published
# under the GPLv3.
#
# Copyright (C) 2016 Daniel Troeder (daniel #at# admin-box #dot# com)
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import logging
import xmlrpclib
import socket
from operator import methodcaller
import datetime
import cPickle

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from netifaces import interfaces, ifaddresses, AF_INET

from srs.models import Game, PlayerAccount, Replay, SldbLeaderboardGame, SldbLeaderboardPlayer, SldbPlayerTSGraphCache, SldbMatchSkillsCache

logger = logging.getLogger("srs.sldb")


#
# SLDB is a service provided by a lobby bot written by Bibim: https://github.com/Yaribz/SLDB
# It has a XMLRPC interface that the website uses: https://github.com/Yaribz/SLDB/blob/master/XMLRPC
#

class SLDBstatusError(Exception):
    def __init__(self, service, status):
        self.service = service
        self.status = status

    def __str__(self):
        return "%s() returned status %d." % (self.service, self.status)


class SLDBbadArgumentError(Exception):
    def __init__(self, arg, val):
        self.argument = arg
        self.value = val

    def __str__(self):
        return "Bad argument '%s': %s" % (self.argument, self.value)


class SLDBConnectionError(Exception):
    pass


rank2skill = {0: 10,
              1: 13,
              2: 16,
              3: 20,
              4: 25,
              5: 30,
              6: 35,
              7: 38}

sldb_gametype2matchtype = {"Duel": "1",
                           "Team": "T",
                           "FFA": "F",
                           "TeamFFA": "G",
                           "Global": "L"
                           }
matchtype2sldb_gametype = {"1": "Duel",
                           "T": "Team",
                           "F": "FFA",
                           "G": "TeamFFA",
                           "L": "Global"
                           }


def skill2rank(trueskill):
    mindiff = 99
    minrank = 0
    for rank, ts in rank2skill.items():
        if abs(ts - trueskill) < mindiff:
            mindiff = abs(ts - trueskill)
            minrank = rank
    return minrank


def privatize_skill(ts):
    return rank2skill[skill2rank(ts)]


def demoskill2float(skill):
    num = "0"
    for s in skill:
        if s.isdigit() or s == ".":
            num += s
    return float(num)


def _my_ip4_addresses():
    ip_list = list()
    for interface in interfaces():
        if AF_INET not in ifaddresses(interface):
            continue
        for link in ifaddresses(interface)[AF_INET]:
            ip_list.append(link['addr'])
    return ip_list


def _query_sldb(service, *args, **kwargs):
    """
    May raise an Exception after settings.SLDB_TIMEOUT seconds or if there was
    a problem with the data/request.
    """
    #    logger.debug("service: %s, args: %s, kwargs: %s", service, args, kwargs)

    #     if settings.DEBUG:
    #         logger.debug("not connecting while in DEBUG")
    #         raise SLDBstatusError(service, -1)

    if not any(ip in settings.SLDB_ALLOWED_IPS for ip in _my_ip4_addresses()):
        # fail fast while developing
        raise SLDBConnectionError("This host is not allowed to connect to SLDB.")

    socket_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(settings.SLDB_TIMEOUT)
    rpc_srv = xmlrpclib.ServerProxy(settings.SLDB_URL)
    rpc = methodcaller(service, settings.SLDB_ACCOUNT, settings.SLDB_PASSWORD, *args, **kwargs)
    try:
        rpc_result = rpc(rpc_srv)
    except Exception as exc:
        logger.error("FIXME: to broad exception handling.")
        logger.exception("Exception in service: %s args: %s, kwargs: %s, Exception: %s", service, args, kwargs, exc)
        raise exc
    else:
        #         logger.debug("%s() returned: %s", service, rpc_result)
        pass
    finally:
        socket.setdefaulttimeout(socket_timeout)

    if rpc_result["status"] != 0:
        logger.debug("rpc_result=%r", rpc_result)
        raise SLDBstatusError(service, rpc_result["status"])

    try:
        return rpc_result["result"] if "result" in rpc_result else rpc_result["results"]
    except KeyError:
        return rpc_result["status"]


def _get_PlayerAccount(accountid, privacy_mode=1, preffered_name=""):
    account, created = PlayerAccount.objects.get_or_create(accountid=accountid, defaults={"countrycode": "??",
                                                                                          "preffered_name": preffered_name,
                                                                                          "sldb_privacy_mode": privacy_mode})
    if created:
        logger.info("Unknown PlayerAccount, accountId: %d, created new PA(%d)", accountid, account.id)
        if privacy_mode == -1:
            try:
                account.sldb_privacy_mode = get_sldb_pref(accountid, "privacyMode")
                account.save()
            except:
                logger.exception("FIXME: to broad exception handling.")
                pass
    if (account.preffered_name == "" or account.preffered_name == "??") and preffered_name:
        account.preffered_name = preffered_name
        account.save()
    return account


def get_sldb_playerskill(game_abbr, accountids, user=None, privatize=True):
    """
    game_abbr: "BA", "ZK" etc from Game.sldb_name
    accountids: [1234, 567]  -- PlayerAccount for those must already exist!
    user: request.user
    privatize: privatize TS depending on privacyMode and logged in user,
               if False exact values are returned regardless of privacyMode
               and user

    If the overall request was OK, but one or more results are bad, no
    exception will be raised, but instead
    skills=[[0.0, 0.0], [0.0, 0.0], [0.0, 0.0], [0.0, 0.0], [0.0, 0.0]] will
    be returned for that accountid.

    SLDB XmlRpc interface docu: https://github.com/Yaribz/SLDB/blob/master/XMLRPC#L1
    """
    #     logger.debug("game: %s accountids: %s user: %s privatize: %s", game_abbr, accountids, user, privatize)

    rpc_skills = _query_sldb("getSkills", game_abbr, accountids)

    for pa_result in rpc_skills:
        pa_result["account"] = _get_PlayerAccount(pa_result["accountId"], privacy_mode=-1)
        if pa_result["status"] != 0:
            pa_result["skills"] = [[0.0, 0.0], [0.0, 0.0], [0.0, 0.0], [0.0, 0.0], [0.0, 0.0]]
            continue
        for i in range(5):
            mu = float(pa_result["skills"][i].split("|")[0])
            si = float(pa_result["skills"][i].split("|")[1])
            pa_result["skills"][i] = [0, 0]
            if privatize:
                if pa_result["privacyMode"] == 0:
                    do_priv = False
                else:
                    if user:
                        do_priv = user.userprofile.accountid != pa_result["accountId"]
                    else:
                        do_priv = True
            else:
                do_priv = False

            if do_priv:
                pa_result["skills"][i][0] = privatize_skill(mu)
            else:
                pa_result["skills"][i][0] = mu
            pa_result["skills"][i][1] = si

            #     logger.debug("returning: %s", rpc_skills)
    return rpc_skills


def get_sldb_pref(accountid, pref):
    """
    get_sldb_pref(130601, "privacyMode") -> {'status': 0, 'result': '0'}

    SLDB XmlRpc interface docu: https://github.com/Yaribz/SLDB/blob/master/XMLRPC#L30
    """
    return _query_sldb("getPref", accountid, pref)


def set_sldb_pref(accountid, pref, value=None):
    """
    set_sldb_pref(130601, "privacyMode", "0") -> {'status': 0}
    "value" is optional, if not provided the preference is set back to default value in SLDB.

    SLDB XmlRpc interface docu: https://github.com/Yaribz/SLDB/blob/master/XMLRPC#L45
    """
    if value:
        return _query_sldb("setPref", accountid, pref, value)
    else:
        return _query_sldb("setPref", accountid, pref)


def get_sldb_match_skills(gameIDs):
    """
    get_sldb_match_skills(["b70f1f270d5a828e24bd446828e0f133"]) ->
    {'status': 0,
     'results': [{'gameId': 'b70f1f270d5a828e24bd446828e0f133',
                  'status': 0,
                  'gameType': 'Duel',
                  'players': [{'accountId': 123456,
                               'privacyMode': 1,
                               'skills': [[12.34, 1.00], [56.78, 2.00], [90.12, 3.00], [34.56, 4.00]],
                               'account': PlayerAccount},
                              {'accountId': 67890,
                               'privacyMode': 1,
                               'skills': [[12.34, 1.00], [56.78, 2.00], [90.12, 3.00], [34.56, 4.00]]
                               'account': PlayerAccount}
                             ]
                 }
                ]
     }

    SLDB XmlRpc interface docu: https://github.com/Yaribz/SLDB/blob/master/XMLRPC#L60
    """
    #     logger.debug("gameIDs: %s", gameIDs)

    # check cache
    SldbMatchSkillsCache.purge_old()
    cache_miss = dict()
    result = list()
    for gameid in gameIDs:
        cache_entry, created = SldbMatchSkillsCache.objects.get_or_create(gameID=gameid, defaults={"text": ""})
        if created or cache_entry.text == "":
            #             logger.debug("MatchSkills cache miss for %s", gameid)
            cache_miss[gameid] = cache_entry
        else:
            #             logger.debug("MatchSkills cache hit  for %s", gameid)
            sldbmatch_unpickled = cPickle.loads(str(cache_entry.text))
            result.append(sldbmatch_unpickled)

    if cache_miss:
        match_skills = _query_sldb("getMatchSkills", cache_miss.keys())
        for match in match_skills:
            if match["status"] != 0:
                logger.error("status: %d for match %s, got: %s", match["status"], match["gameId"], match)
            else:
                for player in match["players"]:
                    player["account"] = _get_PlayerAccount(player["accountId"], player["privacyMode"])
                    for i in range(4):
                        mu = float(player["skills"][i].split("|")[0])
                        si = float(player["skills"][i].split("|")[1])
                        player["skills"][i] = [mu, si]
                dbentry = cache_miss[match["gameId"]]
                dbentry.text = cPickle.dumps(match)
                dbentry.save()
                result.append(match)

    return result


def get_sldb_leaderboards(game, match_types=["1", "T", "F", "G", "L"]):
    """
    get_sldb_leaderboards("BA") -> QuerySet of SldbLeaderboardGame for requested game and gametypes
        Leaderboard data is requested only once per day from SLDB (cached for 1 day)!

    SLDB XmlRpc interface docu: https://github.com/Yaribz/SLDB/blob/master/XMLRPC#93
    """
    #     logger.debug("game: %s match_types: %s", game, match_types)
    # test args
    if game.sldb_name == "":
        raise SLDBbadArgumentError("game", game)
    try:
        [(matchtype2sldb_gametype[match_type], match_type) for match_type in match_types]
    except:
        logger.exception("FIXME: to broad exception handling.")
        raise SLDBbadArgumentError("match_types", match_types)

    refresh_lbg = list()
    for match_type in match_types:
        lbg, created = SldbLeaderboardGame.objects.get_or_create(game=game, match_type=match_type)
        if created or datetime.datetime.now(tz=lbg.last_modified.tzinfo) - lbg.last_modified > datetime.timedelta(1):
            # new entry or older than 1 day -> refresh
            #             logger.debug("Leaderboard cache stale for %s", lbg)
            refresh_lbg.append(lbg)
        else:
            #             logger.debug("Leaderboard cache hit   for %s", lbg)
            pass
    if refresh_lbg:
        query_args = game.sldb_name, [matchtype2sldb_gametype[lbg.match_type] for lbg in refresh_lbg]
        try:
            leaderboards = _query_sldb("getLeaderboards", *query_args)
        except SLDBConnectionError as exc:
            # problem fetching data from SLDB, mark existing data as stale, so it will be retried next website reload
            logger.error("getLeaderboards '%s': %s", query_args, exc)
            for lbg in refresh_lbg:
                lbg.last_modified = datetime.datetime(1970, 1, 1, tzinfo=lbg.last_modified.tzinfo)
                lbg.save()
            leaderboards = list()
        for leaderboard in leaderboards:
            if leaderboard["status"] != 0:
                logger.error("status: %d for gameType %s, got: %s", leaderboard["status"], leaderboard["gameType"],
                             leaderboard)
            else:
                # find corresponding SldbLeaderboardGame
                lbg = SldbLeaderboardGame.objects.get(game=game,
                                                      match_type=sldb_gametype2matchtype[leaderboard["gameType"]])
                rank = 0
                for player in leaderboard["players"]:
                    # save player infos
                    rank += 1
                    defaults = {"account": _get_PlayerAccount(player["accountId"], -1, player["name"]),
                                "trusted_skill": float(player["trustedSkill"]),
                                "estimated_skill": float(player["estimatedSkill"]),
                                "uncertainty": float(player["uncertainty"]),
                                "inactivity": player["inactivity"]}
                    sldb_lb_player, created = SldbLeaderboardPlayer.objects.get_or_create(leaderboard=lbg, rank=rank,
                                                                                          defaults=defaults)
                    if not created:
                        for k, v in defaults.items():
                            setattr(sldb_lb_player, k, v)
                        sldb_lb_player.save()
                # remove unused ranks
                SldbLeaderboardPlayer.objects.filter(leaderboard=lbg, rank__gt=rank).delete()
                # update timestamp
                lbg.last_modified = datetime.datetime.now(tz=lbg.last_modified.tzinfo)
                lbg.save()
    else:
        pass
    return SldbLeaderboardGame.objects.filter(game=game, match_type__in=match_types)


def get_sldb_player_stats(game_abbr, accountid):
    """
    get_sldb_player_stats("BA", 130601) -> {'status': 0,
                                            'results': {'Duel': [12, 34, 5],
                                                        'TeamFFA': [67, 8, 9],
                                                        'FFA': [10, 11, 12],
                                                        'Team': [134, 567, 89]
                                                        }
                                            }
                                            or SLDBstatusError

    SLDB XmlRpc interface docu: https://github.com/Yaribz/SLDB/blob/master/XMLRPC#124
    """
    #     logger.debug("game_abbr: %s accountid: %d", game_abbr, accountid)
    return _query_sldb("getPlayerStats", game_abbr, accountid)


def get_sldb_player_ts_history_graphs(game_abbr, accountid):
    """
    Returns a PNG image of the TrueSkill history of a player.

    SLDB XmlRpc interface docu: https://github.com/Yaribz/SLDB/blob/master/XMLRPC#L141

    :param game_abbr:  str - one of: "BA", "EVO", "KP", "NOTA", "S1944", "TA", "XTA", "ZK" (see "modShortName" in https://github.com/Yaribz/SLDB/blob/master/XMLRPC#L7)
    :param accountid:  int - accountID of playeraccount for which the graph should be fetched
    :return: Dict - SldbPlayerTSGraphCache.as_dict()
            or SLDBstatusError
            or SLDBbadArgumentError
    """
    # check parameters
    try:
        accountid = int(accountid)
        pa = PlayerAccount.objects.get(accountid=accountid)
    except ObjectDoesNotExist:
        raise SLDBbadArgumentError("accountid", accountid)
    try:
        game = Game.objects.get(sldb_name=game_abbr)
    except ObjectDoesNotExist:
        raise SLDBbadArgumentError("game_abbr", game_abbr)

    # check if we a have cached version
    SldbPlayerTSGraphCache.purge_old()
    try:
        cached_graphs = SldbPlayerTSGraphCache.objects.get(account=pa, game=game)
        logger.debug("Cache hit for SldbPlayerTSGraphCache.objects.get(account=%s, game=%s)", pa, game.sldb_name)
        return cached_graphs.as_dict()
    except SldbPlayerTSGraphCache.MultipleObjectsReturned:
        logger.error("More than 1 entry returned for SldbPlayerTSGraphCache.objects.get(account=%s, game=%s). "
                     "Removing all, creating new one.", pa, game.sldb_name)
        cached_graphs = SldbPlayerTSGraphCache.objects.filter(account=pa, game=game)
        for graph in cached_graphs:
            graph.remove_files()
        cached_graphs.delete()
    except SldbPlayerTSGraphCache.DoesNotExist:
        logger.debug("Cache miss for SldbPlayerTSGraphCache.objects.get(account=%s, game=%s)", pa, game.sldb_name)

    # fetch new graphs
    query = _query_sldb("getPlayerSkillGraphs", game_abbr, accountid)
    # this returns either:
    # {   'TeamFFA': {'status': 0, 'graph': <xmlrpclib.Binary instance>},
    #     'Duel'   : {'status': 0, 'graph': <xmlrpclib.Binary instance>},
    #     'Global' : {'status': 0, 'graph': <xmlrpclib.Binary instance>},
    #     'FFA'    : {'status': 0, 'graph': <xmlrpclib.Binary instance>},
    #     'Team'   : {'status': 0, 'graph': <xmlrpclib.Binary instance>}
    # }
    # or SLDBstatusError
    now = datetime.datetime.now(tz=Replay.objects.latest().unixTime.tzinfo)
    graph = SldbPlayerTSGraphCache(game=game, account=pa)
    for match_type, result in query.items():
        if result["status"] == 0:
            path = settings.TS_HISTORY_GRAPHS_PATH + "/%d_%s_%s_%s.png" % (
                accountid, game_abbr, match_type, now.strftime("%Y-%m-%d"))
            open(path, "w").write(result["graph"].data)
        else:
            path = settings.IMG_PATH + "/tsh_nodata.png"
        setattr(graph, "filepath_" + match_type.lower(), path)
    graph.save()
    logger.debug("Created SldbPlayerTSGraphCache: %s", graph)
    return graph.as_dict()
