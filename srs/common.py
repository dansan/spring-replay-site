# This file is part of the "spring relay site / srs" program. It is published
# under the GPLv3.
#
# Copyright (C) 2012 Daniel Troeder (daniel #at# admin-box #dot# com)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.
from django.conf import settings
from srs.models import PlayerAccount

def all_page_infos(request):
    c = {}
    if request.user.is_authenticated():
        try:
            c["logged_in_pa"] = PlayerAccount.objects.get(accountid=request.user.userprofile.accountid)
        except:
            pass

    c["selfurl"] = request.path
    return c
