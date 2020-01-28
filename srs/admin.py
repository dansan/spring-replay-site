# This file is part of the "spring relay site / srs" program. It is published
# under the GPLv3.
#
# Copyright (C) 2016-2020 Daniel Troeder (daniel #at# admin-box #dot# com)
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django.contrib import admin
from .models import AdditionalReplayOwner, Allyteam, ExtraReplayMedia, Game, GameRelease, Map, MapImg, MapOption, ModOption, NewsItem, Player, PlayerAccount, Rating, RatingHistory, Replay, SldbLeaderboardGame, SldbLeaderboardPlayer, Tag, Team, UploadTmp


class PlayerAccountAdmin(admin.ModelAdmin):
    list_display = ("accountid", "id", "preffered_name", "get_names")
    search_fields = ["id", "accountid", "preffered_name", "player__name"]


class PlayerAdmin(admin.ModelAdmin):
    list_display = ("name", "id", "spectator")
    search_fields = ["id", "name", "account__preffered_name"]


class RatingAdmin(admin.ModelAdmin):
    list_display = ("playername", "playeraccount", "game", "match_type", "trueskill_mu")
    search_fields = ["playername"]


class ReplayAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "map_info", "upload_date", "unixTime", "uploader", "gameID", "autohostname")
    search_fields = ["id", "title", "map_info__name", "uploader__username", "gameID"]


class MapAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ["name"]


class MapImgAdmin(admin.ModelAdmin):
    list_display = ("filename", "startpostype")
    search_fields = ["filename"]


class TagAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ["name"]


class GameAdmin(admin.ModelAdmin):
    list_display = ("name", "abbreviation", "sldb_name")
    search_fields = ["name", "abbreviation", "sldb_name", "developer__username"]


class GameReleaseAdmin(admin.ModelAdmin):
    list_display = ("name", "version", "game")
    search_fields = ["name", "version", "game__name"]


class AdditionalReplayOwnerAdmin(admin.ModelAdmin):
    list_display = ("uploader", "additional_owner")
    search_fields = ["uploader", "additional_owner"]


class ExtraReplayMediaAdmin(admin.ModelAdmin):
    list_display = ("uploader", "upload_date", "media", "image", "media_magic_mime", "replay")
    search_fields = ["uploader", "media", "image", "media_magic_mime"]


class NewsItemAdmin(admin.ModelAdmin):
    list_display = ("post_date", "show", "text")
    search_fields = ["post_date", "text"]


class SldbLeaderboardGameAdmin(admin.ModelAdmin):
    list_display = ("last_modified", "game", "match_type")


class SldbLeaderboardPlayerAdmin(admin.ModelAdmin):
    list_display = ("leaderboard", "account", "rank", "trusted_skill", "estimated_skill", "uncertainty", "inactivity")
    search_fields = ["leaderboard__game__name", "leaderboard__game__sldb_name", "account__preffered_name",
                     "account__accountid", "rank"]


admin.site.register(Tag, TagAdmin)
admin.site.register(Map, MapAdmin)
admin.site.register(MapImg, MapImgAdmin)
admin.site.register(Replay, ReplayAdmin)
admin.site.register(Allyteam)
admin.site.register(PlayerAccount, PlayerAccountAdmin)
admin.site.register(Player, PlayerAdmin)
admin.site.register(Team)
admin.site.register(MapOption)
admin.site.register(ModOption)
admin.site.register(NewsItem, NewsItemAdmin)
admin.site.register(UploadTmp)
admin.site.register(Rating, RatingAdmin)
admin.site.register(RatingHistory)
admin.site.register(Game, GameAdmin)
admin.site.register(GameRelease, GameReleaseAdmin)
admin.site.register(AdditionalReplayOwner, AdditionalReplayOwnerAdmin)
admin.site.register(ExtraReplayMedia, ExtraReplayMediaAdmin)
admin.site.register(SldbLeaderboardGame, SldbLeaderboardGameAdmin)
admin.site.register(SldbLeaderboardPlayer, SldbLeaderboardPlayerAdmin)
