from django.conf import settings
from srs.models import *
import logging
import xmlrpclib
import socket

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

def get_sldb_playerskill(game_abbr, accountids, user, privatize):
    """
    game_abbr: "BA", "ZK" etc
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
    socket_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(settings.SLDB_TIMEOUT)
    rpc_srv = xmlrpclib.ServerProxy(settings.SLDB_URL)
    try:
        rpc_skills = rpc_srv.getSkills(settings.SLDB_ACCOUNT, settings.SLDB_PASSWORD, game_abbr, accountids)
    except Exception, e:
        logger.error("Exception in getSkill(..., %s, %s): %s", game_abbr, accountids, e)
        socket.setdefaulttimeout(socket_timeout)
        raise e
    socket.setdefaulttimeout(socket_timeout)
    if rpc_skills["status"] != 0:
        errmsg = "getSkill(..., %s, %s) returned status %d, got: %s" %(game_abbr, accountids, rpc_skills["status"], rpc_skills)
        logger.error(errmsg)
        raise Exception(errmsg)
    else:
        for pa_result in rpc_skills["results"]:
            if pa_result["status"] != 0:
                logger.error("status: %d for accountId %d, got: %s", pa_result["status"], pa_result["accountId"], pa_result)
                pa_result["skills"] = [[0, 0], [0, 0], [0, 0], [0, 0]]
            else:
                for i in range(4):
                    ts = float(pa_result["skills"][i].split("|")[0])
                    si = float(pa_result["skills"][i].split("|")[1])
                    pa_result["skills"][i] = [0, 0]
                    if privatize:
                        pa = PlayerAccount.objects.get(accountid=pa_result["accountId"])
                        if pa.sldb_privacy_mode == 0:
                            do_priv = False
                        else:
                            if user:
                                do_priv = user.get_profile().accountid != pa.accountid
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
