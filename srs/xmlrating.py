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
        rating = pa.get_rating(ga, mt)
    except Exception:
        # unknown user -> return default rating
        if mt in ["T", "F", "G"]: return (25.0, 25.0/3)
        else: return (1500.0, 30.0)

    if mt in ["T", "F", "G"]:
        return (rating.trueskill_mu, rating.trueskill_sigma)
    else:
        return (rating.elo, rating.elo_k)

def authenticate_uploader(username, password):
    user = django.contrib.auth.authenticate(username=username, password=password)

    if user is not None and user.is_active:
        logger.info("Authenticated user '%s' (%d)", user, user.id)
    else:
        raise Exception("Unknown or inactive uploader account or bad password.")

    if user.username not in settings.USERS_ALLOWED_TO_SET_RATINGS_AND_SMURFS:
        raise Exception("Your account is not allowed to change player ratings or unify/separate accounts.")
    else:
        return user

def check_new_rating(rating):
    try:
        return float(rating)
    except ValueError:
        raise Exception("Rating '%s' not a number (float)."%str(rating))

def get_rating_single_user(accountid, game, match_type):
    rating, _ = get_rating_single_user2(accountid, game, match_type)
    return rating

def get_rating_single_user2(accountid, game, match_type):
    try:
        aid = check_accountid(accountid)
        ga  = check_game(game)
        mt  = check_match_type(match_type)
    except Exception, e:
        return error_log_return(e)

    rating, stdev =  get_rating(ga, mt, aid)
    return rating, stdev

def get_rating_multiple_users(accountids, game, match_type):
    ratings_with_stdev = get_rating_multiple_users2(accountids, game, match_type)
    return [(accountid, rating) for (accountid, rating, _) in ratings_with_stdev]

def get_rating_multiple_users2(accountids, game, match_type):

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
        rating, stdev = get_rating(ga, mt, aid)
        result.append((accountid, rating, stdev))
    return result

def set_rating(accountid, game, match_type, rating, username, password, admin_account):
    try:
        _    = authenticate_uploader(username, password)
        return set_rating_authenticated(accountid, game, match_type, rating, admin_account)
    except Exception, e:
        logger.error("accountid=%s game=%s match_type=%s rating=%s username='%s' password=xxxxxx admin_account=%s", accountid, game, match_type, rating, username, admin_account)
        return error_log_return(e)

def set_rating_authenticated(accountid, game, match_type, rating, admin_account):
    logger.info("accountid=%s game=%s match_type=%s rating=%s admin_account=%s", accountid, game, match_type, rating, admin_account)
    try:
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
    try:
        _    = authenticate_uploader(username, password)
        return unify_accounts_authenticated(accountid1, accountid2, admin_accountid)
    except Exception, e:
        logger.error("accountid1=%s accountid2=%s username=%s password=xxxxxx admin_accountid=%s", accountid1, accountid2, username, admin_accountid)
        return error_log_return(e)

def unify_accounts_authenticated(accountid1, accountid2, admin_accountid):
    logger.info("accountid1=%s accountid2=%s admin_accountid=%s", accountid1, accountid2, admin_accountid)

    try:
        acc1   = check_accountid(accountid1)
        acc2   = check_accountid(accountid2)
        adm_id = check_accountid(admin_accountid)
    except Exception, e:
        return error_log_return(e)

    if acc1 == acc2: return acc1

    pa1, _   = PlayerAccount.objects.get_or_create(accountid=acc1, defaults={'accountid': acc1, 'countrycode': "??", 'preffered_name': "??"})
    pa2, _   = PlayerAccount.objects.get_or_create(accountid=acc2, defaults={'accountid': acc2, 'countrycode': "??", 'preffered_name': "??"})
    admin, _ = PlayerAccount.objects.get_or_create(accountid=adm_id, defaults={'accountid': adm_id, 'countrycode': "??", 'preffered_name': "??"})

    all_accounts = pa1.get_all_accounts()
    all_accounts.extend(pa2.get_all_accounts())
    lowest_id = reduce(min, [pa.accountid for pa in all_accounts])

    if pa1 in pa2.get_all_accounts(): return lowest_id

    if AccountUnificationBlocking.objects.filter(account1=pa1, account2__in=pa2.get_all_accounts()).exists() or AccountUnificationBlocking.objects.filter(account1=pa2, account2__in=pa1.get_all_accounts()).exists():
        logger.info("blocking unification of '%s' (acid:%d) and '%s' (acid:%d)", pa1, pa1.accountid, pa2, pa2.accountid)
        return lowest_id

    logger.info("admin(%d) '%s' unifies: acc1(%d): %s AND acc2(%d): %s", adm_id, admin.get_preffered_name(), acc1, pa1.get_all_accounts(), acc2, pa2.get_all_accounts())

    prim_acc = PlayerAccount.objects.get(accountid=lowest_id)
    prim_acc.primary_account = None
    prim_acc.save()

    all_accounts.remove(prim_acc)
    for pa in all_accounts:
        if pa.primary_account == None:
            pa.primary_account = prim_acc
            pa.save()
    all_accounts.insert(0, prim_acc)

    all_account_ids = sorted([pa.accountid for pa in all_accounts])
    all_account_ids_str = reduce(lambda x, y: str(x)+"|%d"%y, all_account_ids)
    acc_uni_log = AccountUnificationLog.objects.create(admin=admin, account1=pa1, account2=pa2, all_accounts=all_account_ids_str)

    all_ratings = Rating.objects.filter(playeraccount__in=prim_acc.get_all_accounts())

    for rating in all_ratings:
        AccountUnificationRatingBackup.objects.create(account_unification_log=acc_uni_log, game=rating.game, match_type=rating.match_type,
                                                      playeraccount=rating.playeraccount, playername=rating.playername,
                                                      elo=rating.elo, elo_k=rating.elo_k,
                                                      glicko=rating.glicko, glicko_rd=rating.glicko_rd, glicko_last_period=rating.glicko_last_period,
                                                      trueskill_mu=rating.trueskill_mu, trueskill_sigma=rating.trueskill_sigma)

    for rating in all_ratings:
        prim_rating = prim_acc.get_rating(game=rating.game, match_type=rating.match_type)
        other_accounts_ratings = all_ratings.filter(game=rating.game, match_type=rating.match_type).exclude(id=prim_rating.id)
        for oar in other_accounts_ratings:
            prim_rating.elo             = max(prim_rating.elo, oar.elo)
            prim_rating.elo_k           = min(prim_rating.elo_k, oar.elo_k)
            prim_rating.glicko          = max(prim_rating.glicko, oar.glicko)
            prim_rating.glicko_rd       = min(prim_rating.glicko_rd, oar.glicko_rd)
            if prim_rating.trueskill_sigma > oar.trueskill_sigma:
                # the other accounts TrueSkill value is more correct / had more matches 
                prim_rating.trueskill_mu    = oar.trueskill_mu
                prim_rating.trueskill_sigma = oar.trueskill_sigma
            #else:
            #   keep prim_rating.TS
        prim_rating.save()
    all_ratings.filter().exclude(playeraccount=prim_acc).delete()

    return lowest_id

def separate_accounts(accountid1, accountid2, username, password, admin_accountid):
    try:
        _    = authenticate_uploader(username, password)
        return separate_accounts_authenticated(accountid1, accountid2, admin_accountid)
    except Exception, e:
        logger.error("accountid1=%s accountid2=%s username=%s password=xxxxxx admin_accountid=%s", accountid1, accountid2, username, admin_accountid)
        return error_log_return(e)

def separate_accounts_authenticated(accountid1, accountid2, admin_accountid):
    from views import revert_unify_accounts
    logger.info("accountid1=%s accountid2=%s admin_accountid=%s", accountid1, accountid2, admin_accountid)
    try:
        acc1   = check_accountid(accountid1)
        acc2   = check_accountid(accountid2)
        adm_id = check_accountid(admin_accountid)

        if acc1 == acc2: return acc1

        pa1   = PlayerAccount.objects.get(accountid=acc1)
        pa2   = PlayerAccount.objects.get(accountid=acc2)
        admin = PlayerAccount.objects.get(accountid=adm_id)
    except Exception, e:
        return error_log_return(e)

    au_log = AccountUnificationLog.objects.filter(account1=pa1, account2=pa2).order_by("-change_date")
    if not au_log.exists():
        au_log = AccountUnificationLog.objects.filter(account1=pa2, account2=pa1).order_by("-change_date")
    if not au_log.exists():
        return error_log_return("Cannot find log entry of previous unification.")
    return revert_unify_accounts(au_log[0], admin, from_xmlrpc=True)
