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

url = 'http://zero-k.info/ContentService.asmx?WSDL'
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
            try:
                user = User.objects.get(last_name=str(accountinfo.LobbyID))
            except:
                user = User.objects.create_user(username=username, last_name=str(accountinfo.LobbyID), password=password, email="django@needs.this") # email, so comments form doesn't ask for it
                user.is_staff = False
                user.is_superuser = False
                logger.info("created User %s (%s)", user.username, user.last_name)
            # password might have changed on the lobby server, we store a hashed version in case server is down to use as fallback
            user.set_password(password)
            user.save()

            userprofile, up_created = UserProfile.objects.get_or_create(accountid=accountinfo.LobbyID,
                                                                        defaults={"user": user,
                                                                                  "accountid": accountinfo.LobbyID,
                                                                                  "timerank": accountinfo.LobbyTimeRank,
                                                                                  "aliases": accountinfo.Name,
                                                                                  "country": accountinfo.Country})
            if up_created: logger.info("created UserProfile(%d) for User %s (%s)", userprofile.id, user.username, user.last_name)

            server_aliases = [accountinfo.Name]
            if hasattr(accountinfo, "Aliases"):
                server_aliases.extend(accountinfo.Aliases.split(","))
            up_aliases     = userprofile.aliases.split(",")
            for s_a in server_aliases:
                if not s_a in up_aliases:
                    if len(userprofile.aliases) > 0: userprofile.aliases += ","
                    userprofile.aliases += s_a
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
            logger.error("Exception while using SOAP to check username/password: %s", e)
            return None
