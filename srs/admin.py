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

class PlayerAccountAdmin(admin.ModelAdmin):
    list_display = ("accountid", "id", "preffered_name", "get_names")
    search_fields = ["id", "accountid", "preffered_name", "primary_account__preffered_name", "player__name"]

class PlayerAdmin(admin.ModelAdmin):
    list_display = ("name", "id", "spectator")
    search_fields = ["id", "name", "account__preffered_name", "account__primary_account__preffered_name"]

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
    search_fields = ["leaderboard__game__name", "leaderboard__game__sldb_name", "account__preffered_name",  "account__accountid", "rank"]

class BAwardsAdmin(admin.ModelAdmin):
    list_display = ("replay", "ecoKillAward1st", "ecoKillAward2nd", "ecoKillAward3rd", "fightKillAward1st", "fightKillAward2nd", "fightKillAward3rd", "effKillAward1st", "effKillAward2nd", "effKillAward3rd", "cowAward", "ecoAward", "dmgRecAward", "sleepAward")
    search_fields = ["replay", "ecoKillAward1st", "ecoKillAward2nd", "ecoKillAward3rd", "fightKillAward1st", "fightKillAward2nd", "fightKillAward3rd", "effKillAward1st", "effKillAward2nd", "effKillAward3rd", "cowAward", "ecoAward", "dmgRecAward", "sleepAward"]

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
admin.site.register(Game)
admin.site.register(GameRelease)
admin.site.register(AdditionalReplayOwner, AdditionalReplayOwnerAdmin)
admin.site.register(ExtraReplayMedia, ExtraReplayMediaAdmin)
admin.site.register(SldbLeaderboardGame, SldbLeaderboardGameAdmin)
admin.site.register(SldbLeaderboardPlayer, SldbLeaderboardPlayerAdmin)
admin.site.register(BAwards, BAwardsAdmin)

admin.site.register(UserProfile)
