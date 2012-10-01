# This file is part of the "spring relay site / srs" program. It is published
# under the GPLv3.
#
# Copyright (C) 2012 Daniel Troeder (daniel #at# admin-box #dot# com)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

from models import *
from lobbyauth.models import UserProfile
from django.contrib import admin

admin.site.register(Tag)
admin.site.register(Map)
admin.site.register(MapImg)
admin.site.register(Replay)
admin.site.register(Allyteam)
admin.site.register(PlayerAccount)
admin.site.register(Player)
admin.site.register(Team)
admin.site.register(MapOption)
admin.site.register(ModOption)
admin.site.register(ReplayFile)
admin.site.register(NewsItem)
admin.site.register(UploadTmp)
admin.site.register(Rating)
admin.site.register(Game)
admin.site.register(GameRelease)

admin.site.register(UserProfile)
