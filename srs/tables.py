# This file is part of the "spring relay site / srs" program. It is published
# under the GPLv3.
#
# Copyright (C) 2012 Daniel Troeder (daniel #at# admin-box #dot# com)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

import django_tables2 as tables
from django_tables2 import A
from django.utils.safestring import mark_safe
from models import Rating, PlayerAccount


class ReplayTable(tables.Table):
    title          = tables.LinkColumn('replay_detail', args=[A('gameID')])
    unixTime       = tables.Column(verbose_name="Match")
    upload_date    = tables.Column(verbose_name="Upload")
    uploader       = tables.Column(orderable=False, accessor=A("uploader.username"))
    download_count = tables.Column(verbose_name="DL")
    comment_count  = tables.Column(verbose_name="C")
    class Meta:
        attrs    = {'class': 'paleblue'}
        order_by = "-upload_date"

class PlayersReplayTable(tables.Table):
    title          = tables.LinkColumn('replay_detail', args=[A('gameID')])
    unixTime       = tables.Column(verbose_name="Date")
    playername     = tables.LinkColumn('player_detail', args=[A('accountid')])
    game           = tables.Column()
    match_type     = tables.Column()
    result         = tables.Column()
    side           = tables.Column()

    class Meta:
        attrs    = {'class': 'paleblue'}
        order_by = "-match_date"

class AutoHostTable(tables.Table):
    name           = tables.LinkColumn('autohost_detail', args=[A('name')])
    count          = tables.Column(verbose_name="# matches")
    class Meta:
        attrs    = {'class': 'paleblue'}
        order_by = "-count"

class TagTable(tables.Table):
    name           = tables.LinkColumn('tag_detail', args=[A('name')])
    count          = tables.Column(verbose_name="# matches")
    class Meta:
        attrs    = {'class': 'paleblue'}
        order_by = "name"

class MapTable(tables.Table):
    name           = tables.LinkColumn('map_detail', args=[A('name')])
    count          = tables.Column(verbose_name="# matches")
    class Meta:
        attrs    = {'class': 'paleblue'}
        order_by = "name"

class GameTable(tables.Table):
    name           = tables.LinkColumn('gamerelease_detail', args=[A('name')])
    count          = tables.Column(verbose_name="# matches")
    class Meta:
        attrs    = {'class': 'paleblue'}
        order_by = "name"

class UserTable(tables.Table):
    name           = tables.LinkColumn('user_detail', args=[A('accountid')])
    count          = tables.Column(verbose_name="# uploads")
    class Meta:
        attrs    = {'class': 'paleblue'}
        order_by = "name"

class CommentTable(tables.Table):
    submit_date     = tables.Column()
    user_name       = tables.LinkColumn('user_detail', args=[A('user.get_profile.accountid')])
    replay          = tables.LinkColumn('replay_detail', args=[A('content_object.gameID')], orderable=False, accessor=A("content_object.title"))
    comment_short   = tables.Column(orderable=False)
    class Meta:
        attrs    = {'class': 'paleblue'}
        order_by = "-submit_date"

class PlayerRatingHistoryTable(tables.Table):
    match_date      = tables.DateTimeColumn(format="Y-m-d H:i:s", verbose_name="Date")
    playername      = tables.LinkColumn('player_detail', args=[A('playeraccount.accountid')])
    game            = tables.Column(accessor=A("game.abbreviation"), verbose_name="Game")
    match_type      = tables.LinkColumn('replay_detail', args=[A('match.gameID')])
    trueskill_mu    = tables.Column(verbose_name="Trueskill")

    class Meta:
        attrs    = {'class': 'paleblue'}
        order_by = "-match_date"

    def render_trueskill_mu(self, value):
        return '%.2f' % value

class RatingHistoryTable(tables.Table):
    match_date      = tables.DateTimeColumn(format="Y-m-d H:i:s", verbose_name="Match_Date")
    algo_change     = tables.Column(verbose_name="Algo")
    game            = tables.Column(accessor=A("game.abbreviation"), verbose_name="Game")
    match_type      = tables.LinkColumn('replay_detail', args=[A('match.gameID')])
    num             = tables.Column(accessor=A("match.num_players"), orderable=False)
    playername      = tables.LinkColumn('player_detail', args=[A('playeraccount.accountid')])
    trueskill_mu    = tables.Column(verbose_name="Trueskill")

    class Meta:
        attrs    = {'class': 'paleblue'}
        order_by = "-match_date"

    def render_trueskill_mu(self, value, record):
        if record.match_type == "O": return ""
        else: return '%.2f' % value

class TSMatchRatingHistoryTable(tables.Table):
    playername      = tables.LinkColumn('player_detail', args=[A('playeraccount.accountid')])
    trueskill_mu    = tables.Column(verbose_name="Trueskill")
    num_matches     = tables.Column(verbose_name="# Matches")

    class Meta:
        attrs    = {'class': 'paleblue'}
        order_by = "-trueskill_mu"

    def render_trueskill_mu(self, value):
        return '%.2f' % value

class MatchRatingHistoryTable(tables.Table):
    playername      = tables.LinkColumn('player_detail', args=[A('playeraccount.accountid')])
    trueskill_mu    = tables.Column(verbose_name="Trueskill")
    num_matches     = tables.Column(verbose_name="# Matches")

    class Meta:
        attrs    = {'class': 'paleblue'}
        order_by = "-elo"

    def render_trueskill_mu(self, value, record):
        if record["match_type"] == "O": return ""
        else: return '%.2f' % value

class PlayerRatingTable(tables.Table):
    game            = tables.Column(accessor=A("game.abbreviation"), verbose_name="Game")
    match_type      = tables.Column()
    trueskill_mu    = tables.Column(verbose_name="Trueskill")

    class Meta:
        attrs    = {'class': 'paleblue'}
        order_by = ("game", "match_type")

    def render_trueskill_mu(self, value):
        return '%.2f' % value

class TSRatingTable(tables.Table):
    playername      = tables.LinkColumn('player_detail', args=[A('playeraccount.accountid')])
    trueskill_mu    = tables.Column(verbose_name="Trueskill")
    num_matches     = tables.Column(verbose_name="# Matches")

    class Meta:
        model = Rating
        fields = ("playername", "trueskill_mu", "num_matches")
        attrs    = {'class': 'paleblue'}
        order_by = "-trueskill_mu"

    def render_trueskill_mu(self, value):
        return '%.2f' % value

class RatingTable(tables.Table):
    playername      = tables.LinkColumn('player_detail', args=[A('playeraccount.accountid')])
    trueskill_mu    = tables.Column(verbose_name="Trueskill")
    num_matches     = tables.Column(verbose_name="# Matches")

    class Meta:
        model = Rating
        fields = ("playername", "elo", "glicko", "trueskill_mu", "num_matches")
        attrs    = {'class': 'paleblue'}
        order_by = "-elo"

    def render_trueskill_mu(self, value, record):
        if record["match_type"] == "O": return ""
        else: return '%.2f' % value

class WinLossTable(tables.Table):
    tag   = tables.Column(orderable=False)
    all = tables.Column(orderable=False, verbose_name="Total")
    win   = tables.Column(orderable=False)
    loss  = tables.Column(orderable=False)
    ratio = tables.Column(orderable=False)

    class Meta:
        attrs    = {'class': 'paleblue'}
