# This file is part of the "spring relay site / srs" program. It is published
# under the GPLv3.
#
# Copyright (C) 2012 Daniel Troeder (daniel #at# admin-box #dot# com)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

#
# implementing a custom django auth backend here
#
# API doc: https://docs.djangoproject.com/en/1.4/topics/auth/#writing-an-authentication-backend
#

import logging
from django.contrib.auth.models import User
from suds.client import Client
from models import UserProfile

url = 'http://zero-k.info/ContentService.svc?WSDL'
logger = logging.getLogger(__package__)

class LobbyBackend():

    def authenticate(self, username=None, password=None):
        logger.info("username=%s password=xxxxxx", username)
        if username == "admin" or username == "root":
            # we reserve this one for us (local django db auth)
            logger.info("username = '%s', not using lobbybackend", username)
            return None
        accountinfo = self.soap_getaccountinfo(username, password)
        logger.debug("accountinfo returned by soap: '%s'", accountinfo)
        if not accountinfo == None:
            accountid = accountinfo.LobbyID
            logger.info("SOAP-login success for username: %s, returned accountid: %d", username, accountid)
            try:
                user = User.objects.get(last_name=str(accountid))
            except:
                logger.info("New account for username: %s. Accountinfo returned by soap: '%s'", username, accountinfo)
                try:
                    user_with_name = User.objects.get(username=username)
                    # a user already exists that has a username that another
                    # account with a differnt accountID (once) had -> modify
                    # username
                    logger.error("Someone has the same username ('%s') but different accountID, user: '%s' (accountID: %s)", username, user_with_name, user_with_name.last_name)
                    # search for unused username
                    counter = 0
                    while User.objects.filter(username=username+"_"+str(counter)).exists():
                        counter += 1
                    username = username+"_"+str(counter)
                except:
                    # no user already exists that has the same username
                    pass
                user = User.objects.create_user(username=username, email="django@needs.this", password="NoNeedToStoreEvenHashedPasswords") # email, so comments form doesn't ask for it
                user.is_staff = False
                user.is_superuser = False
                user.last_name = str(accountid)
                logger.info("created User(%d) %s (accountID: %s)", user.id, user.username, user.last_name)
                user.save()

            timerank  = accountinfo.LobbyTimeRank
            try:
                aliases   = accountinfo.Name
            except:
                aliases   = ""
            try:
                country   = accountinfo.Country
            except:
                country   = "?"

            userprofile, up_created = UserProfile.objects.get_or_create(accountid=accountid,
                                                                        defaults={"user": user,
                                                                                  "timerank": timerank,
                                                                                  "aliases": aliases,
                                                                                  "country": country})
            if up_created: logger.info("created UserProfile(%d) for User(%d) %s (%s)",
                                       userprofile.id, user.id, user.username, user.last_name)

            server_aliases = [accountinfo.Name]
            if hasattr(accountinfo, "Aliases"):
                server_aliases.extend(accountinfo.Aliases.split(","))
            up_aliases     = userprofile.aliases.split(",")
            for s_a in server_aliases:
                if not s_a in up_aliases:
                    if len(userprofile.aliases) > 0: userprofile.aliases += ","
                    userprofile.aliases += s_a
            userprofile.country = country
            userprofile.timerank = timerank
            userprofile.save()

            return user
        else:
            logger.info("Wrong username/password.")
            return None

    def get_user(self, user_id):
        try:
            user = User.objects.get(pk=user_id)
            return user
        except User.DoesNotExist:
            return None

    def soap_getaccountinfo(self, username, password):
        try:
            client = Client(url)
            return client.service.GetAccountInfo(username, password)
        except Exception, e:
            logger.exception("Exception while using SOAP to check username/password: %s", e)
            return None
