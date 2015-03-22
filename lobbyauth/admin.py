# This file is part of the "infolog-upload" program. It is published
# under the GPLv3.
#
# Copyright (C) 2015 Daniel Troeder (daniel #at# admin-box #dot# com)
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django.contrib import admin

from models import *


class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "id", "accountid", "country", "is_developer", "aliases")
    search_fields = ["id", "user__username", "accountid", "country", "aliases"]
    list_filter = ("is_developer",)

admin.site.register(UserProfile, UserProfileAdmin)
