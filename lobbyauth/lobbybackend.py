# This file is part of the "spring relay site / srs" program. It is published
# under the GPLv3.
#
# Copyright (C) 2016 Daniel Troeder (daniel #at# admin-box #dot# com)
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

#
# implementing a custom django auth backend here
#
# API doc: https://docs.djangoproject.com/en/1.4/topics/auth/#writing-an-authentication-backend
#

#
# Version 2: uses xml-rpc to talk to uberserver directly (https://github.com/spring/uberserver/issues/138)
# Version 1: used soap to talk to zero-k webservice
#

import logging
import socket
from django.contrib.auth.models import User
from xmlrpclib import ServerProxy
from models import UserProfile

url = 'https://springrts.com/api/uber/xmlrpc'
logger = logging.getLogger("srs.auth")


class LobbyBackend():
    """
    Authentication backend for django, to use the springrts lobby database.
    """

    def authenticate(self, username=None, password=None):
        """
        Authenticate a user.
        :param str username: lobby account username (case sensitive)
        :param str password: lobby account password (case sensitive)
        :return: User if success or None if bad password/error
        :rtype: django.contrib.auth.models.User or None
        """
        logger.info("username=%s password=xxxxxx", username)
        if username == "admin" or username == "root":
            # we reserve this one for us (local django db auth)
            logger.info("username = '%s', not using lobbybackend", username)
            return None
        accountinfo = self.xmlrpc_getaccountinfo(username, password)
        logger.debug("accountinfo returned by xml-rpc: '%s'", accountinfo)
        if accountinfo["status"] == 0:
            accountid = accountinfo["accountid"]
            logger.info("XML-RPC-login success for username: %s, returned accountid: %d", username, accountid)
            if accountid == 0:
                logger.info("New/Unknown account: accountid == 0, login not allowed.")
                return None
            try:
                user = User.objects.get(last_name=str(accountid))
            except:
                logger.info("New account for username: %s. Accountinfo returned by xml-rpc: '%s'", username,
                            accountinfo)
                try:
                    user_with_name = User.objects.get(username=username)
                    # a user already exists that has a username that another account with a different accountID
                    # (once) had -> modify username
                    logger.info("Someone has the same username ('%s') but different accountID, user: '%s' (accountID: "
                                "%s)", username, user_with_name, user_with_name.last_name)
                    # search for unused username
                    counter = 0
                    while User.objects.filter(username=username + "_" + str(counter)).exists():
                        counter += 1
                    username = username + "_" + str(counter)
                except:
                    # no user already exists that has the same username
                    pass
                user = User.objects.create_user(username=username, email="django@needs.this",
                                                password="NoNeedToStoreEvenHashedPasswords")
                # email, so comments form doesn't ask for it
                user.is_staff = False
                user.is_superuser = False
                user.last_name = str(accountid)
                logger.info("created User(%d) %s (accountID: %s)", user.id, user.username, user.last_name)
                user.save()

            timerank = self._ingame_time_2_rank(accountinfo["ingame_time"])
            aliases = ",".join(accountinfo["aliases"])
            country = accountinfo["country"]

            userprofile, up_created = UserProfile.objects.get_or_create(accountid=accountid,
                                                                        defaults={"user": user,
                                                                                  "timerank": timerank,
                                                                                  "aliases": aliases,
                                                                                  "country": country})
            if up_created:
                logger.info("created UserProfile(%d) for User(%d) %s (%s)",
                            userprofile.id, user.id, user.username, user.last_name)
            else:
                if accountinfo["aliases"] and userprofile.aliases:
                    # merge aliases stored on lobby server and replay server if both are not empty
                    aliases = accountinfo["aliases"]
                    aliases.extend(userprofile.aliases.split(","))
                    aliases = set(aliases)
                    userprofile.aliases = ",".join(aliases)

            userprofile.country = country
            userprofile.timerank = timerank
            userprofile.save()
            return user
        elif accountinfo["status"] == 1:
            logger.info("Wrong username/password.")
            return None
        elif accountinfo["status"] == 2:
            logger.info("Connection problem.")
            return None
        else:
            logger.error("This should not happen. accountinfo[status]=%s", str(accountinfo["status"]))
            return None

    def get_user(self, user_id):
        try:
            user = User.objects.get(pk=user_id)
            return user
        except User.DoesNotExist:
            return None

    def xmlrpc_getaccountinfo(self, username, password):
        """
        Check credentials against lobby database
        :param str username: lobby account username (case sensitive)
        :param str password: lobby account password (case sensitive)
        :return: dict with key "status": 0 = correct username/password, 1 = bad password or user unknown,
        2 = connection problem.
        If status==1 more key/value pairs are present:
        username (str), country (str), ingame_time (int),  aliases (list of str), email (str), accountid (int)
        :rtype: dict
        """
        try:
            client = ServerProxy(url)
            return client.get_account_info(username, password)
        except socket.error, se:
            logger.exception("socket error: errno: %d text: %s", se.errno, se.strerror)
            return {'status': 2}
        except Exception, e:
            logger.exception("Unknown exception: %s", e)
            return {'status': 2}

    @staticmethod
    def _ingame_time_2_rank(ingame_time):
        """
        Convert ingame time in minutes (as stored in lobby DB) to lobby rank (0-7)
        :param int ingame_time:  ingame time in minutes
        :return: lobby rank (0-7)
        :rtype: int
        """
        ranks = (5 * 60, 15 * 60, 30 * 60, 100 * 60, 300 * 60, 1000 * 60, 3000 * 60)
        rank = 0
        for t in ranks:
            if ingame_time >= t:
                rank += 1
        return rank
