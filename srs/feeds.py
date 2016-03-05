# This file is part of the "spring relay site / srs" program. It is published
# under the GPLv3.
#
# Copyright (C) 2016 Daniel Troeder (daniel #at# admin-box #dot# com)
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django.contrib.syndication.views import Feed
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.contrib.comments.feeds import LatestCommentFeed

from models import Replay


class LatestUploadsFeed(Feed):
    title = "Spring replay uploads"
    link = "/"
    description = "Newest replay uploads"
    description_template = 'feeds_replay_description.html'

    @staticmethod
    def items():
        return Replay.objects.order_by('-upload_date')[:20]

    def item_title(self, replay):
        return super(LatestUploadsFeed, self).item_title(replay.title)

    @staticmethod
    def item_pubdate(item):
        return item.unixTime

    @staticmethod
    def item_author_name(item):
        if item.autohostname:
            return item.autohostname
        else:
            return str()


class UploaderFeed(Feed):
    description_template = 'feeds_replay_description.html'

    @staticmethod
    def get_object(request, username):
        return get_object_or_404(User, username=username)

    @staticmethod
    def title(user):
        return "Replays uploaded by %s" % user.username

    @staticmethod
    def link(user):
        return user.get_absolute_url()

    @staticmethod
    def description(user):
        return "Newest replays uploaded by %s" % user.username

    @staticmethod
    def items(user):
        return Replay.objects.filter(uploader=user).order_by('-upload_date')[:20]

    def item_title(self, replay):
        return super(UploaderFeed, self).item_title(replay.title)

    @staticmethod
    def item_pubdate(item):
        return item.unixTime

    @staticmethod
    def item_author_name(item):
        if item.autohostname:
            return item.autohostname
        else:
            return str()


class SRSLatestCommentFeed(LatestCommentFeed):
    @staticmethod
    def item_author_name(item):
        return item.user.username

    def item_title(self, item):
        dots = "..." if len(item.comment) > 50 else ""
        return super(SRSLatestCommentFeed, self).item_title(item.user.username + ": " + item.comment[:50] + dots)

    def item_description(self, item):
        return super(SRSLatestCommentFeed, self).item_description(item.user.username + ": " + item.comment)
