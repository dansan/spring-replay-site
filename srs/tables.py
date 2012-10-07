# This file is part of the "spring relay site / srs" program. It is published
# under the GPLv3.
#
# Copyright (C) 2012 Daniel Troeder (daniel #at# admin-box #dot# com)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

import django_tables2 as tables
from django_tables2 import A
from models import Rating


class ReplayTable(tables.Table):
    title          = tables.LinkColumn('replay_detail', args=[A('gameID')])
    unixTime       = tables.Column(verbose_name="Match")
    upload_date    = tables.Column(verbose_name="Upload")
    uploader       = tables.Column()
    downloads      = tables.Column(accessor="replayfile.download_count", orderable=False, verbose_name="DL")
    comments       = tables.Column(orderable=False, verbose_name="C")
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
    name           = tables.LinkColumn('gamerelease_detail', args=[A('name')])
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
    replay          = tables.LinkColumn('replay_detail', args=[A('content_object.gameID')], orderable=False, accessor=A("content_object.title"))
    comment_short   = tables.Column(orderable=False)
    class Meta:
        attrs    = {'class': 'paleblue'}
        order_by = "-submit_date"

class PlayerRatingHistoryTable(tables.Table):
    match_date      = tables.DateTimeColumn(format="Y-m-d H:i:s", verbose_name="Date")
    game            = tables.Column(accessor=A("game.abbreviation"), verbose_name="Game")
    match_type      = tables.LinkColumn('replay_detail', args=[A('match.gameID')])
    elo             = tables.Column()
    glicko          = tables.Column()
    trueskill_mu    = tables.Column(verbose_name="Trueskill")

    class Meta:
        attrs    = {'class': 'paleblue'}
        order_by = "match_date"

    def render_elo(self, value, record):
        if record.match_type != "1": return ""
        else: return '%.2f' % value
    def render_glicko(self, value, record):
        if record.match_type != "1": return ""
        else: return '%.2f' % value
    def render_trueskill_mu(self, value):
        return '%.2f' % value

class RatingHistoryTable(tables.Table):
    match_date      = tables.DateTimeColumn(format="Y-m-d H:i:s", verbose_name="Match_Date")
    algo_change     = tables.Column(verbose_name="Algo")
    game            = tables.Column(accessor=A("game.abbreviation"), verbose_name="Game")
    match_type      = tables.LinkColumn('replay_detail', args=[A('match.gameID')])
    num             = tables.Column(accessor=A("match.num_players"), orderable=False)
    playername      = tables.LinkColumn('player_detail', args=[A('playeraccount.accountid')])
    elo             = tables.Column()
    glicko          = tables.Column()
    trueskill_mu    = tables.Column(verbose_name="Trueskill")

    class Meta:
        attrs    = {'class': 'paleblue'}
        order_by = "match_date"

    def render_elo(self, value):
        return '%.2f' % value
    def render_glicko(self, value):
        return '%.2f' % value
    def render_trueskill_mu(self, value):
        return '%.2f' % value

class TSMatchRatingHistoryTable(tables.Table):
    playername      = tables.LinkColumn('player_detail', args=[A('playeraccount.accountid')])
    trueskill_mu    = tables.Column(verbose_name="Trueskill")

    class Meta:
        attrs    = {'class': 'paleblue'}
        order_by = "-trueskill_mu"

    def render_trueskill_mu(self, value):
        return '%.2f' % value

class MatchRatingHistoryTable(tables.Table):
    playername      = tables.LinkColumn('player_detail', args=[A('playeraccount.accountid')])
    elo             = tables.Column()
    glicko          = tables.Column()
    trueskill_mu    = tables.Column(verbose_name="Trueskill")

    class Meta:
        attrs    = {'class': 'paleblue'}
        order_by = "-elo"

    def render_elo(self, value):
        return '%.2f' % value
    def render_glicko(self, value):
        return '%.2f' % value
    def render_trueskill_mu(self, value):
        return '%.2f' % value

class PlayerRatingTable(tables.Table):
    playername      = tables.LinkColumn('player_detail', args=[A('playeraccount.accountid')])
    game            = tables.Column(accessor=A("game.abbreviation"), verbose_name="Game")
    match_type      = tables.Column()
    elo             = tables.Column()
    glicko          = tables.Column()
    trueskill_mu    = tables.Column(verbose_name="Trueskill")

    class Meta:
        attrs    = {'class': 'paleblue'}
        order_by = "game"

    def render_elo(self, value, record):
        if record.match_type != "1": return ""
        else: return '%.2f' % value
    def render_glicko(self, value, record):
        if record.match_type != "1": return ""
        else: return '%.2f' % value
    def render_trueskill_mu(self, value):
        return '%.2f' % value

class TSRatingTable(tables.Table):
    playername      = tables.LinkColumn('player_detail', args=[A('playeraccount.accountid')])
    game            = tables.Column(accessor=A("game.abbreviation"), verbose_name="Game")
    trueskill_mu    = tables.Column(verbose_name="Trueskill")

    class Meta:
        model = Rating
        fields = ("playername", "game", "trueskill_mu")
        attrs    = {'class': 'paleblue'}
        order_by = "-trueskill_mu"

    def render_trueskill_mu(self, value):
        return '%.2f' % value

class RatingTable(tables.Table):
    playername      = tables.LinkColumn('player_detail', args=[A('playeraccount.accountid')])
    game            = tables.Column(accessor=A("game.abbreviation"), verbose_name="Game")
    elo             = tables.Column()
    glicko          = tables.Column()
    trueskill_mu    = tables.Column(verbose_name="Trueskill")

    class Meta:
        model = Rating
        fields = ("playername", "game", "elo", "glicko", "trueskill_mu")
        attrs    = {'class': 'paleblue'}
        order_by = "-elo"

    def render_elo(self, value):
        return '%.2f' % value
    def render_glicko(self, value):
        return '%.2f' % value
    def render_trueskill_mu(self, value):
        return '%.2f' % value

class WinLossTable(tables.Table):
    tag   = tables.Column(orderable=False)
    all = tables.Column(orderable=False, verbose_name="Total")
    win   = tables.Column(orderable=False)
    loss  = tables.Column(orderable=False)
    ratio = tables.Column(orderable=False)

    class Meta:
        attrs    = {'class': 'paleblue'}
