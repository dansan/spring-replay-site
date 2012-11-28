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
    list_display = ("accountid", "preffered_name", "get_names")
    search_fields = ["accountid", "preffered_name", "primary_account__preffered_name", "player__name"]

class PlayerAdmin(admin.ModelAdmin):
    list_display = ("name", "spectator")
    search_fields = ["name", "account__preffered_name", "account__primary_account__preffered_name"]

class RatingAdmin(admin.ModelAdmin):
    list_display = ("playername", "playeraccount", "game", "match_type", "elo", "trueskill_mu")
    search_fields = ["playername"]
     
class ReplayAdmin(admin.ModelAdmin):
    list_display = ("title", "map_info", "upload_date", "unixTime", "uploader", "gameID", "autohostname")
    search_fields = ["title", "map_info__name", "uploader__username", "gameID"]
       
class MapAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ["name"]
    
class MapImgAdmin(admin.ModelAdmin):
    list_display = ("filename", "startpostype")
    search_fields = ["filename"]
    
class TagAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ["name"]

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
admin.site.register(NewsItem)
admin.site.register(UploadTmp)
admin.site.register(Rating, RatingAdmin)
admin.site.register(RatingHistory)
admin.site.register(Game)
admin.site.register(GameRelease)

admin.site.register(UserProfile)
