# This file is part of the "spring relay site / srs" program. It is published
# under the GPLv3.
#
# Copyright (C) 2012 Daniel Troeder (daniel #at# admin-box #dot# com)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.
from django.core.context_processors import csrf
from django.db.models import Count

import operator

from models import *

def all_page_infos(request):
    c = {}
    c.update(csrf(request))
    c["total_replays"]   = Replay.objects.count()
    c["top_tags"]        = Tag.objects.annotate(num_replay=Count('replay')).order_by('-num_replay')[:20]
    c["top_maps"]        = Map.objects.annotate(num_replay=Count('replay')).order_by('-num_replay')[:20]
    tp = []
    for pa in PlayerAccount.objects.all():
        tp.append((Player.objects.filter(account=pa, spectator=False).count(), Player.objects.filter(account=pa)[0]))
    tp.sort(key=operator.itemgetter(0), reverse=True)
    c["top_players"] = [p[1] for p in tp[:20]]
    c["latest_comments"] = Comment.objects.reverse()[:5]
    return c
