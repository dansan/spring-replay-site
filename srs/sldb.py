# This file is part of the "spring relay site / srs" program. It is published
# under the GPLv3.
#
# Copyright (C) 2013 Daniel Troeder (daniel #at# admin-box #dot# com)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django.conf import settings
from srs.models import *
import logging
import xmlrpclib
import socket
from operator import methodcaller

logger = logging.getLogger(__package__)


rank2skill = {0: 10,
              1: 13,
              2: 16,
              3: 20,
              4: 25,
              5: 30,
              6: 35,
              7: 38}

def skill2rank(ts):
    if ts <25:
        if ts >= 20:
            return 3
        elif ts >= 16:
            return 2
        elif ts >= 13:
            return 1
        else:
            return 0
    else:
        if ts < 30:
            return 4
        elif ts < 35:
            return 5
        elif ts < 38:
            return 6
        else:
            return 7

def privatize_skill(ts):
    return rank2skill[skill2rank(ts)]

def demoskill2float(skill):
    num = "0"
    for s in skill:
        if s.isdigit() or s == ".":
            num += s
    return float(num)

def _query_sldb(service, *args, **kwargs):
    socket_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(settings.SLDB_TIMEOUT)
    rpc_srv = xmlrpclib.ServerProxy(settings.SLDB_URL)
    rpc = methodcaller(service, settings.SLDB_ACCOUNT, settings.SLDB_PASSWORD, *args, **kwargs)
    try:
        rpc_skills = rpc(rpc_srv)
    except Exception, e:
        logger.exception("Exception in service: %s args: %s, kwargs: %s, Exception: %s", service, args, kwargs, e)
        raise e
    finally:
        socket.setdefaulttimeout(socket_timeout)
    return rpc_skills

def _get_PlayerAccount(accountid, privacy_mode):
    account, created = PlayerAccount.objects.get_or_create(accountid=accountid, defaults={"countrycode": "??", "preffered_name": "", "sldb_privacy_mode": privacy_mode})
    if created:
        logger.error("Unknown PlayerAccount, accountId: %d, created new PA(%d)", accountid, account.id)
        if privacy_mode == -1:
            pm = get_sldb_pref(accountid, "privacyMode")
            if pm["status"] == 0:
                account.sldb_privacy_mode = pm["result"]
            else:
                account.sldb_privacy_mode = 1
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

    May raise an Exception after settings.SLDB_TIMEOUT seconds or if there was
    a problem with the data/request.
    If the overall request was OK, but one or more results are bad, no
    exception will be raised, but instead skills=[0.0, 0.0, 0.0, 0.0] will be
    returned.

SLDB XmlRpc interface docu provided by bibim:

getSkills parameters: login (string), password (string), modShortName (string), accountIds (array of ints)
    modShortName: BA,EVO,KP,NOTA,S1944,TA,XTA,ZK
It returns a map with following keys: status (int), results (array of maps):
"status"   values: 0: OK, 1: authentication failed, 2: invalid params (the "results" key is only present if status=0)
"results"  is an array of maps having following keys: accountId (int), status (int), privacyMode (int), skills (array)
  "status"   values: 0: OK, 1: invalid accountId, 2: unknown skill (user not rated yet) (the privacyMode and skills keys are only present if status=0)
  "skills"   is an array of 5 strings containing skill data in following order:
                 Duel.mu|Duel.sigma , Ffa.mu|Ffa.sigma , Team.mu|Team.sigma , TeamFfa.mu|TeamFfa.sigma , Global.mu|Global.sigma
    """
    logger.debug("game: %s accountids: %s user: %s privatize: %s", game_abbr, accountids, user, privatize)

    rpc_skills = _query_sldb("getSkills", game_abbr, accountids)

    if rpc_skills["status"] != 0:
        errmsg = "getSkill(..., %s, %s) returned status %d, got: %s" %(game_abbr, accountids, rpc_skills["status"], rpc_skills)
        logger.error(errmsg)
        raise Exception(errmsg)
    else:
        for pa_result in rpc_skills["results"]:
            if pa_result["status"] != 0:
                logger.error("status: %d for accountId %d, got: %s", pa_result["status"], pa_result["accountId"], pa_result)
                pa_result["skills"] = [[0, 0], [0, 0], [0, 0], [0, 0], [0, 0]]
            else:
                for i in range(5):
                    mu = float(pa_result["skills"][i].split("|")[0])
                    si = float(pa_result["skills"][i].split("|")[1])
                    pa_result["skills"][i] = [0, 0]
                    if privatize:
                        if pa_result["privacyMode"] == 0:
                            do_priv = False
                        else:
                            if user:
                                do_priv = user.get_profile().accountid != pa_result["accountId"]
                            else:
                                do_priv = True
                    else:
                        do_priv = False

                    if do_priv:
                        pa_result["skills"][i][0] = privatize_skill(mu)
                    else:
                        pa_result["skills"][i][0] = mu
                    pa_result["skills"][i][1] = si
            pa_result["account"] = _get_PlayerAccount(pa_result["accountId"], pa_result["privacyMode"])

        logger.debug("returning: %s", rpc_skills["results"])
        return rpc_skills["results"]

def get_sldb_pref(accountid, pref):
    """
    get_sldb_pref(130601, "privacyMode") -> {'status': 0, 'result': '0'}

SLDB XmlRpc interface docu provided by bibim:

getPref parameters: login (string), password (string), accountId (int), prefName (string)
returns a map with following keys: status (int), result (string)
   "status" values: 0: OK, 1: authentication failed, 2: invalid params (the "result" key is only present if status=0)
    """
    return _query_sldb("getPref", accountid, pref)

def set_sldb_pref(accountid, pref, value=None):
    """
    set_sldb_pref(130601, "privacyMode", "0") -> {'status': 0}
    "value" is optional, if not provided the preference is set back to default value in SLDB.

SLDB XmlRpc interface docu provided by bibim:

setPref parameters: login (string), password (string), accountId (int), prefName (string) [, value (string)]
   "value" is optional, if not provided the preference is set back to default value in SLDB.
returns a map with only one key: status (int)
   "status" values are the same as for getPref (the preference is only updated if status=0)
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

SLDB XmlRpc interface docu provided by bibim:

"getMatchSkills" XmlRpc service takes the following parameters: login (string), password (string), gameIds (array of strings).
It returns a map with following keys: status (int), results (array of maps).

"status" values: 0: OK, 1: authentication failed, 2: invalid params (the "results" key is only present if status=0)
"results" is an array of maps having following keys: gameId (string), status (int), gameType (string), players (array of maps)
    "status" values: 0: OK, 1: invalid gameId value, 2: unknown or unrated gameId (the "gameType" and "players" keys are only present if status=0)
    "gameType" values: "Duel", "FFA", "Team", "TeamFFA"
    "players" is an array of maps having following keys: accountId (int), privacyMode (int), skills (array of strings)
        "skills" is an array of 4 strings containing skill data in following order:
            muBefore|sigmaBefore , muAfter|sigmaAfter , globalMuBefore|globalSigmaBefore , globalMuAfter|globalSigmaAfter

Only the ratings specific to the gameType of the gameId and the global ratings are provided, as other ratings don't change.
    """
    logger.debug("gameIDs: %s", gameIDs)
    match_skills = _query_sldb("getMatchSkills", gameIDs)
    if match_skills["status"] != 0:
        errmsg = "getMatchSkills(..., %s) returned status %d, got: %s" %(gameIDs, match_skills["status"], match_skills)
        logger.error(errmsg)
        raise Exception(errmsg)
    else:
        for match in match_skills["results"]:
            if match["status"] != 0:
                logger.error("status: %d for match %s, got: %s", match["status"], match["gameId"], match)
            else:
                for player in match["players"]:
                    player["account"] = _get_PlayerAccount(player["accountId"], player["privacyMode"])
                    for i in range(4):
                        mu = float(player["skills"][i].split("|")[0])
                        si = float(player["skills"][i].split("|")[1])
                        player["skills"][i] = [mu, si]
    return match_skills

def get_sldb_leaderboard(game_abbr, gametypes=["Duel", "FFA", "Team", "TeamFFA", "Global"]):
    """
    get_sldb_leaderboard("BA") ->
        {'status': 0,
         'results': [{'gameType': 'Duel',
                      'status': 0
                      'players': [{'accountId': 17034,
                                   'estimatedSkill': 36.27,
                                   'inactivity': 5,
                                   'name': 'Teddy',
                                   'trustedSkill': 33.41,
                                   'uncertainty': 0.95},
                                  {...},
                                 ],
                     },
                     {'gameType': 'FFA',
                     'status': 0
                     'players': [{...},
                                ],
                     }
                     {'gameType': 'FFA' ...},
                     {'gameType': 'TeamFFA' ...},
                     {'gameType': 'Global' ...}
                    ]
        }

SLDB XmlRpc interface docu provided by bibim:

getLeaderboards XmlRpc service takes the following parameters: login (string), password (string), modShortName (string), gameTypes (array of strings)
    allowed gameType values: "Duel", "FFA", "Team", "TeamFFA", "Global"
It returns a map with following keys: status (int), results (array of maps).

"status" values: 0: OK, 1: authentication failed, 2: invalid params (the "results" key is only present if status=0)
"results" is an array of maps having following keys: gameType (string), status (int), players (array of maps)
    "status" values: 0: OK, 1: invalid gameType (the "players" key is only present if status=0)
    "players" is an array of maps having following keys: accountId (int), name (string), inactivity (int), trustedSkill (string), estimatedSkill (string), uncertainty (string)
        "trustedSkill", "estimatedSkill" and "uncertainty" are transmitted as strings to avoid rounding approximations when sent as floats.
        "name" is provided in case you want to show the same names as SLDB

The leaderboard size is 20, as when saying !leaderboard to SLDB. But the returned players array can be of smaller size (and even empty for totally unrated mods), in case not enough players have been rated yet.

    """
    logger.debug("game_abbr: %s gametypes: %s", game_abbr, gametypes)
    leaderboards = _query_sldb("getLeaderboards", game_abbr, gametypes)
    if leaderboards["status"] != 0:
        errmsg = "getLeaderboards(..., %s, %s) returned status %d, got: %s" %(game_abbr, gametypes, leaderboards["status"], leaderboards)
        logger.error(errmsg)
        raise Exception(errmsg)
    else:
        for leaderboard in leaderboards["results"]:
            if leaderboard["status"] != 0:
                logger.error("status: %d for gameType %s, got: %s", leaderboard["status"], leaderboard["gameType"], leaderboard)
            else:
                for player in leaderboard["players"]:
                    player["account"] = _get_PlayerAccount(player["accountId"], -1)
                    player["estimatedSkill"] = float(player["estimatedSkill"])
                    player["trustedSkill"] = float(player["trustedSkill"])
                    player["uncertainty"] = float(player["uncertainty"])
    return leaderboards

def get_sldb_player_stats(game_abbr, accountid):
    """
    get_sldb_player_stats("BA", 130601) -> {'status': 0,
                                            'results': {'Duel': [12, 34, 5],
                                                        'TeamFFA': [67, 8, 9],
                                                        'FFA': [10, 11, 12],
                                                        'Team': [134, 567, 89]
                                                        }
                                            }

SLDB XmlRpc interface docu provided by bibim:

getPlayerStats XmlRpc service takes the following parameters: login (string), password (string), modShortName (string), accountId (int)
It returns a map with following keys: status (int), results (hash of arrays).

"status" values: 0: OK, 1: authentication failed, 2: invalid params (the "results" key is only present if status=0)
"results" is a hash indexed by gameType ("Duel", "FFA", "Team", "TeamFFA"), giving the following stats array for each one of these game types: nbOfGamesLost (int), nbOfGamesWon (int), nbOfGamesUndecided (int)
    """
    logger.debug("game_abbr: %s accountid: %d", game_abbr, accountid)
    return _query_sldb("getPlayerStats", game_abbr, accountid)
