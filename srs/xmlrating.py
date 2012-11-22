# This file is part of the "spring relay site / srs" program. It is published
# under the GPLv3.
#
# Copyright (C) 2012 Daniel Troeder (daniel #at# admin-box #dot# com)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

import django.contrib.auth

from models import *
import settings

import logging
logger = logging.getLogger(__package__)

def error_log_return(msg):
    logger.error("-1 %s", msg)
    return "-1 %s"%msg

def check_game(game):
    try:
        return Game.objects.get(abbreviation=game)
    except Exception:
        raise Exception("Unknown game name (abbreviation): '%s'."%str(game))

def check_accountid(accountid):
    try:
        return int(accountid)
    except ValueError:
        raise Exception("Accountid '%s' not a number (int)."%str(accountid))

def check_match_type(match_type):
    mt = str(match_type).upper()
    if mt not in ["1", "T", "F", "G"]:
        raise Exception("Bad match_type '%s' (must be one of '1'/'T'/'F'/'G')."%match_type)
    else:
        return mt

def get_rating(ga, mt, aid):
    try:
        pa = PlayerAccount.objects.get(accountid=aid)
    except Exception:
        # unknown user -> return default rating
        if mt in ["T", "F", "G"]: return 25.0
        else: return 1500.0

    if mt in ["T", "F", "G"]:
        return pa.get_rating(ga, mt).trueskill_mu
    else:
        return pa.get_rating(ga, mt).elo

def authenticate_uploader(username, password):
    user = django.contrib.auth.authenticate(username=username, password=password)

    if user is not None and user.is_active:
        logger.info("Authenticated user '%s' (%d)", user, user.id)
    else:
        raise Exception("Unknown or inactive uploader account or bad password.")

    if user.username not in settings.USERS_ALLOWED_TO_SET_RATINGS:
        raise Exception("Your account is not allowed to change player ratings.")
    else:
        return user

def check_new_rating(rating):
    try:
        return float(rating)
    except ValueError:
        raise Exception("Rating '%s' not a number (float)."%str(rating))

def get_rating_single_user(accountid, game, match_type):
    logger.debug("accountid=%s game=%s match_type=%s", accountid, game, match_type)

    try:
        aid = check_accountid(accountid)
        ga  = check_game(game)
        mt  = check_match_type(match_type)
    except Exception, e:
        return error_log_return(e)

    return get_rating(ga, mt, aid)

def get_rating_multiple_users(accountids, game, match_type):
    logger.debug("accountids=%s game=%s match_type=%s", accountids, game, match_type)

    try:
        ga  = check_game(game)
        mt  = check_match_type(match_type)
    except Exception, e:
        return error_log_return(e)

    if type(accountids) != list:
        return error_log_return("First argument type must be list/array.")

    result = list()
    for accountid in accountids:
        aid = check_accountid(accountid)
        rating = get_rating(ga, mt, aid)
        result.append((accountid, rating))
    return result

def set_rating(accountid, game, match_type, rating, username, password, admin_account):
    logger.debug("accountid=%s game=%s match_type=%s rating=%s username='%s' password=xxxxxx admin_account=%s", accountid, game, match_type, rating, username, admin_account)

    try:
        _    = authenticate_uploader(username, password)
        rat  = check_new_rating(rating)
        acid = check_accountid(accountid)
        adid = check_accountid(admin_account)
        ga   = check_game(game)
        mt   = check_match_type(match_type)
    except Exception, e:
        return error_log_return(e)

    pa, _ = PlayerAccount.objects.get_or_create(accountid=acid, defaults={'accountid': acid, 'countrycode': "??", 'preffered_name': "??"})
    aa, _ = PlayerAccount.objects.get_or_create(accountid=adid, defaults={'accountid': adid, 'countrycode': "??", 'preffered_name': "??"})
    pa_rating = pa.get_rating(ga, mt)
    if mt in ["T", "F", "G"]:
        pa_rating.trueskill_mu = rat
        pa_rating.trueskill_sigma = 4.0
        algo_change = "T"
        RatingAdjustmentHistory.objects.create(algo_change=algo_change, admin=aa, game=ga, match_type=mt, playeraccount=pa, trueskill_mu=rat, trueskill_sigma=4.0)
    else:
        pa_rating.elo = rat
        algo_change = "E"
        RatingAdjustmentHistory.objects.create(algo_change=algo_change, admin=aa, game=ga, match_type=mt, playeraccount=pa, elo=rat)
    pa_rating.save()

    return get_rating_single_user(accountid, game, match_type)
