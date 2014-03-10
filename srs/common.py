# This file is part of the "spring relay site / srs" program. It is published
# under the GPLv3.
#
# Copyright (C) 2012 Daniel Troeder (daniel #at# admin-box #dot# com)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.
from django.core.context_processors import csrf
from django.conf import settings

from models import Tag, Map, SiteStats, update_stats, Game
from django.contrib.comments import Comment
from srs.models import PlayerAccount

def all_page_infos(request):
    c = {}
    c.update(csrf(request))
    try:
        sist = SiteStats.objects.get(id=1)
    except:
        update_stats()
        sist = SiteStats.objects.get(id=1)

    if request.user.is_authenticated():
        try:
            c["logged_in_pa"] = PlayerAccount.objects.get(accountid=request.user.userprofile.accountid)
        except:
            pass

    c["total_replays"]   = sist.replays
    if sist.tags: c["top_tags"] = [Tag.objects.get(id=int(x)) for x in sist.tags.split('|')]
    if sist.maps: c["top_maps"] = [Map.objects.get(id=int(x)) for x in sist.maps.split('|')]
    if sist.players: c["top_players"] = [PlayerAccount.objects.get(id=int(x)) for x in sist.players.split('|')]
    if sist.comments: c["latest_comments"] = [Comment.objects.get(id=int(x)) for x in sist.comments.split('|')]
    c["all_games"] = Game.objects.all()
    c["selfurl"] = request.path
    c["JQUERY_JS_URL"] = settings.JQUERY_JS_URL
    c["JQUERYUI_CSS_URL"] = settings.JQUERYUI_CSS_URL
    c["JQUERYUI_JS_URL"] = settings.JQUERYUI_JS_URL
    return c
