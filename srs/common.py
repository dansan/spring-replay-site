# This file is part of the "spring relay site / srs" program. It is published
# under the GPLv3.
#
# Copyright (C) 2016-2020 Daniel Troeder (daniel #at# admin-box #dot# com)
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import get_object_or_404
from django.utils.datastructures import MultiValueDictKeyError

from .models import Game, PlayerAccount, Replay


def all_page_infos(request):
    c = {}
    try:
        gameid = int(request.GET["game_pref"])
        request.session.modified = (
            True  # force a reload in the client to update the top menu
        )
        request.session["game_pref"] = gameid
        if (
            request.user.is_authenticated
            and request.user.userprofile.game_pref != gameid
            and not request.user.userprofile.game_pref_fixed
        ):
            request.user.userprofile.game_pref = gameid
            request.user.userprofile.save()
    except (TypeError, ValueError, MultiValueDictKeyError):
        # request.GET["game_pref"] not set (or not an int)
        pass
    if request.user.is_authenticated:
        try:
            c["logged_in_pa"] = PlayerAccount.objects.get(
                accountid=request.user.userprofile.accountid
            )
        except ObjectDoesNotExist:
            pass
        if not request.session.get("game_pref"):
            request.session["game_pref"] = request.user.userprofile.game_pref
    c["all_games_mainmenu"] = Game.objects.all()
    c["selfurl"] = request.path
    gids = request.session.get("page_history", [])
    c["page_history"] = Replay.objects.filter(gameID__in=gids)
    if request.session.get("game_pref") and request.session["game_pref"] > 0:
        game_pref = request.session["game_pref"]
        c["game_pref"] = game_pref
        c["game_pref_obj"] = get_object_or_404(Game, id=game_pref)
        c["game_pref_browse"] = "game={}".format(game_pref)
    return c
