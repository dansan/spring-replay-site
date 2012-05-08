# This file is part of the "spring relay site / srs" program. It is published
# under the GPLv3.
#
# Copyright (C) 2012 Daniel Troeder (daniel #at# admin-box #dot# com)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    user      = models.OneToOneField(User)
    accountid = models.IntegerField(unique=True)
    timerank  = models.IntegerField()
    aliases   = models.CharField(max_length=2048)
    country   = models.CharField(max_length=2)

    def __unicode__(self):
        return "profile for %s"%self.user.username
