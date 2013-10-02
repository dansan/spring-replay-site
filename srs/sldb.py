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
    """
    logger.debug("game: %s accountids: %s user: %s privatize: %s", game_abbr, accountids, user, privatize)

    rpc_skills = _query_sldb("getSkills", game_abbr, accountids)

#
# "status"   values: 0: OK, 1: authentication failed, 2: invalid params (the "results" key is only present if status=0)
# "results"  is an array of maps having following keys: accountId (int), status (int), privacyMode (int), skills (array)
#     "status"   values: 0: OK, 1: invalid accountId, 2: unknown skill (user not rated yet) (the privacyMode and skills keys are only present if status=0)
#     "skills"   is an array of 5 strings containing skill data in following order:
#                Duel.mu|Duel.sigma , Ffa.mu|Ffa.sigma , Team.mu|Team.sigma , TeamFfa.mu|TeamFfa.sigma , Global.mu|Global.sigma
#
    if rpc_skills["status"] != 0:
        errmsg = "getSkill(..., %s, %s) returned status %d, got: %s" %(game_abbr, accountids, rpc_skills["status"], rpc_skills)
        logger.error(errmsg)
        raise Exception(errmsg)
    else:
        for pa_result in rpc_skills["results"]:
            if pa_result["status"] != 0:
                logger.info("status: %d for accountId %d, got: %s", pa_result["status"], pa_result["accountId"], pa_result)
                pa_result["skills"] = [[0, 0], [0, 0], [0, 0], [0, 0], [0, 0]]
            else:
                for i in range(5):
                    ts = float(pa_result["skills"][i].split("|")[0])
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
                        pa_result["skills"][i][0] = privatize_skill(ts)
                    else:
                        pa_result["skills"][i][0] = ts
                    pa_result["skills"][i][1] = si
            try:
                pa_result["account"] = PlayerAccount.objects.get(accountid=pa_result["accountId"])
            except Exception, e:
                logger.error("Unknown PlayerAccount(%d): %s", pa_result["accountId"], e)
                pass
        logger.debug("returning: %s", rpc_skills["results"])
        return rpc_skills["results"]

def get_sldb_pref(accountid, pref):
    """
    get_sldb_pref(130601, "privacyMode")

    returns a dict with following keys: status (int), result (string)
        "status" values: 0: OK, 1: authentication failed, 2: invalid params
        the "result" key is only present if status=0
    """
    return _query_sldb("getPref", accountid, pref)

def set_sldb_pref(accountid, pref, value=None):
    """
    set_sldb_pref(130601, "privacyMode", "0")
    "value" is optional, if not provided the preference is set back to default value in SLDB.

    returns a dict with only one key: status (int)
        "status" values are the same as for getPref (the preference is only updated if status=0)
    """
    if value:
        return _query_sldb("setPref", accountid, pref, value)
    else:
        return _query_sldb("setPref", accountid, pref)
