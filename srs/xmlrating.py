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

    if user.username not in settings.USERS_ALLOWED_TO_SET_RATINGS_AND_SMURFS:
        raise Exception("Your account is not allowed to change player ratings or unify accounts.")
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

def unify_accounts(accountid1, accountid2, username, password, admin_accountid):
    logger.debug("accountid1=%s accountid2=%s username=%s password=xxxxxx admin_accountid=%s", accountid1, accountid2, username, admin_accountid)

    try:
        _    = authenticate_uploader(username, password)
        acc1   = check_accountid(accountid1)
        acc2   = check_accountid(accountid2)
        adm_id = check_accountid(admin_accountid)
    except Exception, e:
        return error_log_return(e)

    if acc1 == acc2: return acc1

    pa1, _   = PlayerAccount.objects.get_or_create(accountid=acc1, defaults={'accountid': acc1, 'countrycode': "??", 'preffered_name': "??"})
    pa2, _   = PlayerAccount.objects.get_or_create(accountid=acc2, defaults={'accountid': acc1, 'countrycode': "??", 'preffered_name': "??"})
    admin, _ = PlayerAccount.objects.get_or_create(accountid=adm_id, defaults={'accountid': adm_id, 'countrycode': "??", 'preffered_name': "??"})

    if pa1 in pa2.get_all_accounts(): return pa2.get_all_accounts()[0].accountid

    logger.info("admin(%d) '%s' unifies: acc1(%d): %s AND acc2(%d): %s", adm_id, admin.get_preffered_name(), acc1, pa1.get_all_accounts(), acc2, pa2.get_all_accounts())

    all_accounts = pa1.get_all_accounts()
    all_accounts.extend(pa2.get_all_accounts())

    lowest_id = reduce(min, [pa.accountid for pa in all_accounts])
    prim_acc = PlayerAccount.objects.get(accountid=lowest_id)

    prim_acc.primary_account = None
    prim_acc.save()

    all_accounts.remove(prim_acc)
    for pa in all_accounts:
        pa.primary_account = prim_acc
        pa.save()

    all_accounts.insert(0, prim_acc)
    all_account_ids = sorted([pa.accountid for pa in all_accounts])
    all_account_ids_str = reduce(lambda x, y: str(x)+"|%d"%y, all_account_ids)
    AccountUnificationLog.objects.create(admin=admin, account1=pa1, account2=pa2, all_accounts=all_account_ids_str)

    return lowest_id
