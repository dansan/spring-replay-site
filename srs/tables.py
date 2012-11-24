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
from models import Rating, RatingAdjustmentHistory, PlayerAccount, AccountUnificationLog


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
    playername      = tables.LinkColumn('player_detail', args=[A('playeraccount.accountid')])
    game            = tables.Column(accessor=A("game.abbreviation"), verbose_name="Game")
    match_type      = tables.LinkColumn('replay_detail', args=[A('match.gameID')])
    elo             = tables.Column()
    glicko          = tables.Column()
    trueskill_mu    = tables.Column(verbose_name="Trueskill")

    class Meta:
        attrs    = {'class': 'paleblue'}
        order_by = "-match_date"

    def render_elo(self, value, record):
        if record.match_type in ["1", "O"]: return '%.2f' % value
        else: return ""
    def render_glicko(self, value, record):
        if record.match_type in ["1", "O"]: return '%.2f' % value
        else: return ""
    def render_trueskill_mu(self, value):
        return '%.2f' % value

class Tourney1v1RatingHistoryTable(tables.Table):
    match_date      = tables.DateTimeColumn(format="Y-m-d H:i:s", verbose_name="Match_Date")
    playername      = tables.LinkColumn('player_detail', args=[A('playeraccount.accountid')])
    title           = tables.LinkColumn('replay_detail', args=[A('gameID')])
    elo             = tables.Column()
    num_matches     = tables.Column(verbose_name="# Matches")

    class Meta:
        attrs    = {'class': 'paleblue'}
        order_by = "-match_date"

    def render_elo(self, value):
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
        order_by = "-match_date"

    def render_elo(self, value):
        return '%.2f' % value
    def render_glicko(self, value, record):
        if record.match_type == "O": return ""
        else: return '%.2f' % value
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
    elo             = tables.Column()
    glicko          = tables.Column()
    trueskill_mu    = tables.Column(verbose_name="Trueskill")
    num_matches     = tables.Column(verbose_name="# Matches")

    class Meta:
        attrs    = {'class': 'paleblue'}
        order_by = "-elo"

    def render_elo(self, value):
        return '%.2f' % value
    def render_glicko(self, value, record):
        if record["match_type"] == "O": return ""
        else: return '%.2f' % value
    def render_trueskill_mu(self, value, record):
        if record["match_type"] == "O": return ""
        else: return '%.2f' % value

class TourneyMatchRatingHistoryTable(tables.Table):
    playername      = tables.LinkColumn('player_detail', args=[A('playeraccount.accountid')])
    elo             = tables.Column()
    glicko          = tables.Column()
    trueskill_mu    = tables.Column(verbose_name="Trueskill")
    num_matches     = tables.Column(verbose_name="# Matches")
    match_type      = tables.Column(verbose_name="Tourney")

    class Meta:
        attrs    = {'class': 'paleblue'}
        order_by = "-match_type"

    def render_elo(self, value):
        return '%.2f' % value
    def render_glicko(self, value):
        return '%.2f' % value
    def render_trueskill_mu(self, value):
        return '%.2f' % value
    def render_match_type(self, value):
        if value == "O": return "yes"
        else           : return "no"

class PlayerRatingTable(tables.Table):
    game            = tables.Column(accessor=A("game.abbreviation"), verbose_name="Game")
    match_type      = tables.Column()
    elo             = tables.Column()
    glicko          = tables.Column()
    trueskill_mu    = tables.Column(verbose_name="Trueskill")

    class Meta:
        attrs    = {'class': 'paleblue'}
        order_by = "game, match_type"

    def render_elo(self, value, record):
        if record.match_type in ["1", "O"]: return '%.2f' % value
        else: return ""
    def render_glicko(self, value, record):
        if record.match_type in ["1", "O"]: return '%.2f' % value
        else: return ""
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
    elo             = tables.Column()
    glicko          = tables.Column()
    trueskill_mu    = tables.Column(verbose_name="Trueskill")
    num_matches     = tables.Column(verbose_name="# Matches")

    class Meta:
        model = Rating
        fields = ("playername", "elo", "glicko", "trueskill_mu", "num_matches")
        attrs    = {'class': 'paleblue'}
        order_by = "-elo"

    def render_elo(self, value):
        return '%.2f' % value
    def render_glicko(self, value, record):
        if record["match_type"] == "O": return ""
        else: return '%.2f' % value
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

class RatingAdjustmentHistoryTable(tables.Table):
    change_date     = tables.DateTimeColumn(format='d.m.Y H:i:s', verbose_name="Date")
    admin           = tables.LinkColumn('player_detail', args=[A('admin.accountid')], accessor=A("admin.get_preffered_name"))
    playeraccount   = tables.LinkColumn('player_detail', args=[A('playeraccount.accountid')], accessor=A("playeraccount.get_preffered_name"), verbose_name="Player")
    game            = tables.Column(accessor=A("game.abbreviation"), verbose_name="Game")
    match_type      = tables.Column(verbose_name="Match")
    elo             = tables.Column()
    trueskill_mu    = tables.Column(verbose_name="Trueskill")

    class Meta:
        model = RatingAdjustmentHistory
        fields = ("change_date", "admin", "playeraccount", "game", "match_type", "elo", "trueskill_mu")
        attrs    = {'class': 'paleblue'}
        order_by = "-change_date"

    def render_elo(self, value, record):
        if record.algo_change != "E": return ""
        else: return '%.2f' % value
    def render_trueskill_mu(self, value, record):
        if record.match_type != "T": return ""
        else: return '%.2f' % value

class AccountUnificationLogTable(tables.Table):
    change_date     = tables.DateTimeColumn(format='d.m.Y H:i:s', verbose_name="Date")
    admin           = tables.LinkColumn('player_detail', args=[A('admin.accountid')], accessor=A("admin.get_preffered_name"))
    account1        = tables.LinkColumn('player_detail', args=[A('account1.accountid')], accessor=A("account1.preffered_name"), verbose_name="Player 1")
    account2        = tables.LinkColumn('player_detail', args=[A('account2.accountid')], accessor=A("account2.preffered_name"), verbose_name="Player 2")
    all_accounts    = tables.Column()

    class Meta:
        model = AccountUnificationLog
        fields = ("change_date", "admin", "account1", "account2", "all_accounts")
        attrs    = {'class': 'paleblue'}
        order_by = "-change_date"

    def render_all_accounts(self, value):
        acc_ids = value.split("|")
        result = str()
        for acc in acc_ids:
            try:
                int(acc) # paranoid check, before inserting something bad into html
            except:
                continue
            pa = PlayerAccount.objects.get(accountid=acc)
            result += '<a href="'+pa.get_absolute_url()+'">'+pa.preffered_name+'</a> '
        return mark_safe(result)
