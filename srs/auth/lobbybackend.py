# This file is part of the "spring relay site / srs" program. It is published
# under the GPLv3.
#
# Copyright (C) 2012 Daniel Troeder (daniel #at# admin-box #dot# com)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

#
# implementing a custom django-registration backend here
#
# API doc: http://docs.b-list.org/django-registration/0.8/backend-api.html
#

import logging
from django.contrib.auth.models import User
from suds.client import Client

url = 'http://zero-k.info/ContentService.asmx?WSDL'
logger = logging.getLogger(__package__)

class LobbyBackend():

    def authenticate(self, username=None, password=None):
        logger.debug("username=%s password=xxxxxx", username)
        if username == "admin":
            # we reserve this one for us (local django db auth)
            return None
        login_valid = self.soap_check(username, password)
        logger.debug("soap_check() returned '%s'", login_valid)
        if login_valid:
            try:
                user = User.objects.get(username=username)
                # password might have changed on the lobby server,
                # we store a hashed version in case server is down
                # to use as fallback
                user.set_password(password)
                user.save()
                logger.debug("User '%s' existed.", user.username)
            except User.DoesNotExist:
                user = User.objects.create_user(username=username, password=password, email="django@needs.this") # email, so comments form doesnt ask for it
                user.is_staff = False
                user.is_superuser = False
                user.save()
                logger.info("Created user '%s'.", user.username)
            return user
        else:
            logger.debug("Wrong username/password.")
        return None

    def get_user(self, user_id):
        try:
            user = User.objects.get(pk=user_id)
            return user
        except User.DoesNotExist:
            return None

    def soap_check(self, username, password):
        try:
            client = Client(url)
            return client.service.VerifyAccountData(username, password)
        except Exception, e:
            logger.error("Exception while using SOAP to check username/password: %s", e)
            return False
