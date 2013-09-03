from django.conf import settings
from srs.models import *
import logging
import xmlrpclib

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

def get_sldb_playerskill(game_abbr, accountids, user, privatize):
    """
    game_abbr: "BA", "ZK" etc
    accountids: [1234, 567]  -- PlayerAccount for those must already exist!
    user: request.user
    privatize: privatize TS depending on privacyMode and logged in user,
               if False exact values are returned regardless of privacyMode
               and user
    """
    logger.debug("game: %s accountids: %s user: %s privatize: %s", game_abbr, accountids, user, privatize)
    rpc_srv = xmlrpclib.ServerProxy(settings.SLDB_URL)
    try:
        rpc_skills = rpc_srv.getSkills(settings.SLDB_ACCOUNT, settings.SLDB_PASSWORD, game_abbr, accountids)
    except Exception, e:
        logger.error("Exception in getSkill(..., %s, %s): %s", game_abbr, accountids, e)
        raise e

    if rpc_skills["status"] != 0:
        errmsg = "getSkill(..., %s, %s) returned status %d" %(game_abbr, accountids, rpc_skills["status"])
        logger.error(errmsg)
        raise Exception(errmsg)
    else:
        for pa_result in rpc_skills["results"]:
            if pa_result["status"] != 0:
                logger.error("status: %d for accountId %d", pa_result["status"], pa_result["accountId"])
                pa_result["skills"] = [0.0, 0.0, 0.0, 0.0]
            else:
                logger.debug("accountId: %d privacyMode: %d skills: %s", pa_result["accountId"], pa_result["privacyMode"], pa_result["skills"])
                for i in range(4):
                    ts = float(pa_result["skills"][i].split("|")[0])
                    if privatize:
                        pa = PlayerAccount.objects.get(accountid=pa_result["accountId"])
                        if pa.sldb_privacy_mode == 0:
                            do_priv = False
                        else:
                            if user:
                                do_priv = user.get_profile().accountid != pa.accountid
                            else:
                                do_priv = True
                    if do_priv:
                        pa_result["skills"][i] = privatize_skill(ts)
                    else:
                        pa_result["skills"][i] = ts
                logger.debug("returned skills: %s", pa_result["skills"])
        return rpc_skills["results"]
