# This file is part of the "spring relay site / srs" program. It is published
# under the GPLv3.
#
# Copyright (C) 2012 Daniel Troeder (daniel #at# admin-box #dot# com)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.


from models import *

import logging
logger = logging.getLogger(__package__)

def error_log_return(msg):
    logger.error("-1 %s", msg)
    return "-1 %s"%msg


def xmlrpc_rate_single_user(accountid, game, match_type):
    logger.info("accountid=%s game=%s match_type=%s", accountid, game, match_type)
    try:
        aid =  int(accountid)
    except ValueError, e:
        return error_log_return("accountid not a number: %s"%str(e))

    try:
        pa = PlayerAccount.objects.get(accountid=accountid)
    except Exception, e:
        return error_log_return("Bad player account: %s"%str(e))

    try:
        ga = Game.objects.get(abbreviation=game)
    except Exception, e:
        return error_log_return("Bad game name: %s"%str(e))

    if match_type not in ["1", "T", "F", "G"]:
        return error_log_return("Bad match_type (must be one of 1/T/F/G)")

    rating = pa.get_rating(ga, match_type)

    if match_type == "1":
        logger.debug("return %f", rating.elo)
        return rating.elo
    else:
        logger.debug("return %f", rating.trueskill_mu)
        return rating.trueskill_mu

