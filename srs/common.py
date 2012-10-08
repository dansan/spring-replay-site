# This file is part of the "spring relay site / srs" program. It is published
# under the GPLv3.
#
# Copyright (C) 2012 Daniel Troeder (daniel #at# admin-box #dot# com)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.
from django.core.context_processors import csrf

from models import Tag, Map, Player, SiteStats, update_stats, Game
from django.contrib.comments import Comment

def all_page_infos(request):
    c = {}
    c.update(csrf(request))
    try:
        sist = SiteStats.objects.get(id=1)
    except:
        update_stats()
        sist = SiteStats.objects.get(id=1)

    c["total_replays"]   = sist.replays
    if sist.tags:     c["top_tags"]        = Tag.objects.filter(id__in=sist.tags.split('|'))
    if sist.maps:     c["top_maps"]        = Map.objects.filter(id__in=sist.maps.split('|'))
    if sist.players:  c["top_players"]     = Player.objects.filter(id__in=sist.players.split('|'))
    if sist.comments: c["latest_comments"] = Comment.objects.filter(id__in=sist.comments.split('|'))
    c["all_games"] = Game.objects.all()
    return c
