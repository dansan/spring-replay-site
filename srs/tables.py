# This file is part of the "spring relay site / srs" program. It is published
# under the GPLv3.
#
# Copyright (C) 2012 Daniel Troeder (daniel #at# admin-box #dot# com)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

import django_tables2 as tables
from django_tables2 import A


class ReplayTable(tables.Table):
    title          = tables.LinkColumn('replay_detail', args=[A('gameID')])
    unixTime       = tables.Column()
    upload_date    = tables.Column()
    uploader       = tables.Column()
    downloads      = tables.Column(accessor="replayfile.download_count", orderable=False)
    comments       = tables.Column(orderable=False)
    class Meta:
        attrs    = {'class': 'paleblue'}
        order_by = "-upload_date"

class TagTable(tables.Table):
    name           = tables.LinkColumn('tag_detail', args=[A('name')])
    replays        = tables.Column(orderable=False)
    class Meta:
        attrs    = {'class': 'paleblue'}
        order_by = "name"

class MapTable(tables.Table):
    name           = tables.LinkColumn('map_detail', args=[A('name')])
    replays        = tables.Column(orderable=False)
    class Meta:
        attrs    = {'class': 'paleblue'}
        order_by = "name"

class PlayerTable(tables.Table):
    name           = tables.LinkColumn('player_detail', args=[A('accid')])
    replay_count   = tables.Column(orderable=False)
    spectator_count= tables.Column(orderable=False)
    class Meta:
        attrs    = {'class': 'paleblue'}
        order_by = "name"

class GameTable(tables.Table):
    name           = tables.LinkColumn('game_detail', args=[A('name')])
    replays        = tables.Column(orderable=False)
    class Meta:
        attrs    = {'class': 'paleblue'}
        order_by = "name"

class UserTable(tables.Table):
    username       = tables.LinkColumn('user_detail', args=[A('username')])
    replays_uploaded = tables.Column(orderable=False)
    class Meta:
        attrs    = {'class': 'paleblue'}
        order_by = "username"

class CommentTable(tables.Table):
    submit_date     = tables.Column()
    user_name       = tables.LinkColumn('user_detail', args=[A('user_name')])
    replay          = tables.LinkColumn('replay_detail', args=[A('content_object.gameID')], orderable=False)
    comment_short   = tables.Column(orderable=False)
    class Meta:
        attrs    = {'class': 'paleblue'}
        order_by = "-submit_date"
