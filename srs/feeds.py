# This file is part of the "spring relay site / srs" program. It is published
# under the GPLv3.
#
# Copyright (C) 2016-2020 Daniel Troeder (daniel #at# admin-box #dot# com)
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django.contrib.auth.models import User
from django.contrib.syndication.views import Feed
from django.shortcuts import get_object_or_404
from django_comments.feeds import LatestCommentFeed

from .models import Game, GameRelease, Replay


class LatestUploadsFeed(Feed):
    title = "Spring replay uploads"
    link = "/"
    description = "Newest replay uploads"
    description_template = 'feeds_replay_description.html'

    def items(self):
        return Replay.objects.order_by('-upload_date')[:20]

    def item_title(self, replay):
        return super(LatestUploadsFeed, self).item_title(replay.title)

    def item_pubdate(self, item):
        return item.unixTime

    def item_author_name(self, item):
        if item.autohostname:
            return item.autohostname
        else:
            return str()


class GameFeed(Feed):
    description_template = 'feeds_replay_description.html'

    def get_object(self, request, game):
        return get_object_or_404(Game, name=game)

    def title(self, game):
        return "Replay uploads for %s" % game.name

    def link(self, game):
        return game.get_absolute_url()

    def description(self, game):
        return "Newest %s replays" % game.name

    def items(self, game):
        gr_names = GameRelease.objects.filter(game=game).values_list('name', flat=True)
        return Replay.objects.filter(gametype__in=gr_names).order_by('-upload_date')[:20]

    def item_title(self, replay):
        return super(GameFeed, self).item_title(replay.title)

    def item_pubdate(self, item):
        return item.unixTime

    def item_author_name(self, item):
        if item.autohostname:
            return item.autohostname
        else:
            return str()


class UploaderFeed(Feed):
    description_template = 'feeds_replay_description.html'

    def get_object(self, request, username):
        return get_object_or_404(User, username=username)

    def title(self, user):
        return "Replays uploaded by %s" % user.username

    def link(self, user):
        return user.get_absolute_url()

    def description(self, user):
        return "Newest replays uploaded by %s" % user.username

    def items(self, user):
        return Replay.objects.filter(uploader=user).order_by('-upload_date')[:20]

    def item_title(self, replay):
        return super(UploaderFeed, self).item_title(replay.title)

    def item_pubdate(self, item):
        return item.unixTime

    def item_author_name(self, item):
        if item.autohostname:
            return item.autohostname
        else:
            return str()


class SRSLatestCommentFeed(LatestCommentFeed):

    def item_author_name(self, item):
        return item.user.username

    def item_title(self, item):
        dots = "..." if len(item.comment) > 50 else ""
        return super(SRSLatestCommentFeed, self).item_title(item.user.username + ": " + item.comment[:50] + dots)

    def item_description(self, item):
        return super(SRSLatestCommentFeed, self).item_description(item.user.username + ": " + item.comment)
