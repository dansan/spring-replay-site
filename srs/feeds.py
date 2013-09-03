from django.contrib.syndication.views import Feed
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.contrib.comments.feeds import LatestCommentFeed

from models import Replay, AccountUnificationLog

class LatestUploadsFeed(Feed):
    title = "Spring replay uploads"
    link = "/"
    description = "Newest replay uploads"
    description_template = 'feeds_replay_description.html'

    def items(self):
        return Replay.objects.order_by('-upload_date')[:20]

    def item_title(self, replay):
        return replay.title

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
        return replay.title

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
        return item.user.username+": "+item.comment[:50]+dots

    def item_description(self, item):
        return item.user.username+": "+item.comment

class SmurfsFeed(Feed):
    title = "Accounts unified"
    link = "/account_unification_history/"
    description = "Newest unified accounts"
    description_template = 'feeds_acc_uni_description.html'

    def items(self):
        return AccountUnificationLog.objects.order_by('-change_date')[:20]

    def item_title(self, aulog):
        return aulog.admin.preffered_name + " : " +  aulog.account1.preffered_name + " + " +  aulog.account2.preffered_name

    def item_pubdate(self, item):
        return item.change_date

    def item_author_name(self, item):
        return item.admin.preffered_name
