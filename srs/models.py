# This file is part of the "spring relay site / srs" program. It is published
# under the GPLv3.
#
# Copyright (C) 2012 Daniel Troeder (daniel #at# admin-box #dot# com)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

import logging
import operator

from django.db import models
from django.contrib.auth.models import User
from django.contrib.comments import Comment
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.db.models import Count

import settings

logger = logging.getLogger(__package__)

class Tag(models.Model):
    name            = models.CharField(max_length=128, unique=True)

    def __unicode__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return ('srs.views.tag', [self.name])

    def replays(self):
        return Replay.objects.filter(tags__name=self.name).count()

class Map(models.Model):
    name            = models.CharField(max_length=128)
    startpos        = models.CharField(max_length=1024, blank=True, null = True)
    height          = models.IntegerField()
    width           = models.IntegerField()

    def __unicode__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return ('srs.views.rmap', [self.name])

    def replays(self):
        return Replay.objects.filter(map_info__name=self.name).count()

class MapImg(models.Model):
    filename        = models.CharField(max_length=128)
    startpostype    = models.IntegerField(blank=True, null = True, verbose_name='-1 means full image')
    map_info        = models.ForeignKey(Map)

    def __unicode__(self):
        return self.map_info.name+" type:"+str(self.startpostype)

    def get_absolute_url(self):
        return (settings.STATIC_URL+"maps/"+self.filename)

class ReplayFile(models.Model):
    filename        = models.CharField(max_length=256)
    path            = models.CharField(max_length=256)
    ori_filename    = models.CharField(max_length=256)
    download_count  = models.IntegerField()

    def __unicode__(self):
        return self.filename[:20]

class Replay(models.Model):
    versionString   = models.CharField(max_length=32)
    gameID          = models.CharField(max_length=32, unique=True)
    unixTime        = models.DateTimeField(verbose_name='date of match')
    wallclockTime   = models.CharField(max_length=32, verbose_name='length of match')
    autohostname    = models.CharField(max_length=128, blank=True, null = True)
    gametype        = models.CharField(max_length=256)
    startpostype    = models.IntegerField(blank=True, null = True)
    title           = models.CharField(max_length=256)
    short_text      = models.CharField(max_length=50)
    long_text       = models.CharField(max_length=513)
    notcomplete     = models.BooleanField()
    map_info        = models.ForeignKey(Map, blank=True, null = True)
    map_img         = models.ForeignKey(MapImg, blank=True, null = True)
    tags            = models.ManyToManyField(Tag)
    uploader        = models.ForeignKey(User)
    upload_date     = models.DateTimeField(auto_now_add=True)
    replayfile      = models.ForeignKey(ReplayFile)

    def __unicode__(self):
        return self.title+" "+self.unixTime.strftime("%Y-%m-%d")

    @models.permalink
    def get_absolute_url(self):
        return ('srs.views.replay', [str(self.gameID)])

    def comments(self):
        r_t = ContentType.objects.get_for_model(Replay)
        return Comment.objects.filter(object_pk=str(self.pk), content_type=r_t.pk).count()

    def was_succ_uploaded(self):
        return not UploadTmp.objects.filter(replay=self).exists()

    class Meta:
        get_latest_by = 'upload_date'
        ordering = ['-upload_date']

class Allyteam(models.Model):
    numallies       = models.IntegerField()
    startrectbottom = models.FloatField(blank=True, null = True)
    startrectleft   = models.FloatField(blank=True, null = True)
    startrectright  = models.FloatField(blank=True, null = True)
    startrecttop    = models.FloatField(blank=True, null = True)
    winner          = models.BooleanField()
    replay          = models.ForeignKey(Replay)

class PlayerAccount(models.Model):
    accountid       = models.IntegerField(unique=True)
    countrycode     = models.CharField(max_length=2)
    names           = models.CharField(max_length=2048, verbose_name="(re)names")
    aka             = models.ForeignKey("self", blank=True, null = True, verbose_name="other accounts")

    def __unicode__(self):
        return str(self.accountid)+u" "+self.names[:15]

    def replay_count(self):
        return Player.objects.filter(account=self).count()

    def spectator_count(self):
        return Player.objects.filter(account=self, spectator=True).count()

    class Meta:
        ordering = ['accountid']


class Player(models.Model):
    account         = models.ForeignKey(PlayerAccount, blank=True, null = True)
    name            = models.CharField(max_length=128)
    rank            = models.IntegerField()
    spectator       = models.BooleanField()
    team            = models.ForeignKey("Team", blank=True, null = True)
    replay          = models.ForeignKey(Replay)

    def __unicode__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return ('srs.views.player', [self.account.accountid])

    class Meta:
        ordering = ['name']

class Team(models.Model):
    allyteam        = models.ForeignKey(Allyteam)
    handicap        = models.IntegerField()
    rgbcolor        = models.CharField(max_length=23)
    side            = models.CharField(max_length=32)
    startposx       = models.IntegerField(blank=True, null = True)
    startposy       = models.IntegerField(blank=True, null = True)
    startposz       = models.IntegerField(blank=True, null = True)
    teamleader      = models.ForeignKey(Player, related_name="+")
    replay          = models.ForeignKey(Replay)

    def __unicode__(self):
        return self.side

class MapModOption(models.Model):
    name            = models.CharField(max_length=128)
    value           = models.CharField(max_length=512)
    replay          = models.ForeignKey(Replay)

    def __unicode__(self):
        return self.name

class MapOption(MapModOption):
    pass

class ModOption(MapModOption):
    pass

class NewsItem(models.Model):
    text            = models.CharField(max_length=256)
    post_date       = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return self.text[:50]

class UploadTmp(models.Model):
    replay          = models.ForeignKey(Replay)

    def __unicode__(self):
        return self.replay.__unicode__()

# not the most beautiful model, but efficient
class SiteStats(models.Model):
    replays         = models.IntegerField()
    tags            = models.CharField(max_length=1000)
    maps            = models.CharField(max_length=1000)
    players         = models.CharField(max_length=1000)
    comments        = models.CharField(max_length=1000)
    last_modified   = models.DateTimeField(auto_now=True)


def update_stats():
    replays  = Replay.objects.count()
    tags     = Tag.objects.annotate(num_replay=Count('replay')).order_by('-num_replay')[:20]
    maps     = Map.objects.annotate(num_replay=Count('replay')).order_by('-num_replay')[:20]
    tp = []
    for pa in PlayerAccount.objects.all():
        p = Player.objects.filter(account=pa)
        if p.exists():   # p can be empty, because when a replay is deleted the Players are deleted, but the PlayerAccounts not   
            tp.append((Player.objects.filter(account=pa, spectator=False).count(), p[0]))
    tp.sort(key=operator.itemgetter(0), reverse=True)
    players  = [p[1] for p in tp[:20]]
    comments = Comment.objects.reverse()[:5]

    if tags.exists():     tags_s     = reduce(lambda x, y: str(x)+"|%d"%y, [t.id for t in tags])
    else:                 tags_s     = ""
    if maps.exists():     maps_s     = reduce(lambda x, y: str(x)+"|%d"%y, [m.id for m in maps])
    else:                 maps_s     = ""
    if players:           players_s  = reduce(lambda x, y: str(x)+"|%d"%y, [p.id for p in players])
    else:                 players_s  = ""
    if comments.exists(): comments_s = reduce(lambda x, y: str(x)+"|%d"%y, [c.id for c in comments])
    else:                 comments_s = ""

    sist, created = SiteStats.objects.get_or_create(id=1, defaults={'replays':replays, 'tags':tags_s, 'maps':maps_s, 'players':players_s, 'comments':comments_s})
    if not created:
        sist.replays = replays
        sist.tags = tags_s
        sist.maps = maps_s
        sist.players = players_s
        sist.comments = comments_s
        sist.save()


# TODO: use a proxy model for this
User.get_absolute_url = lambda self: "/user/"+self.username+"/"
User.replays_uploaded = lambda self: Replay.objects.filter(uploader=self).count()

# TODO: use a proxy model for this
Comment.replay = lambda self: self.content_object.__unicode__()
Comment.comment_short = lambda self: self.comment[:50]+"..."

# automatically log each DB object delete
@receiver(post_delete)
def obj_del_callback(sender, instance, using, **kwargs):
    # Session obj has u'str encoded hex key as pk
    logger.debug("%s.delete(%s) : '%s'", instance.__class__.__name__, instance.pk, instance)

# automatically refresh statistics when a replay is created or modified
@receiver(post_save, sender=Replay)
def replay_save_callback(sender, instance, using, **kwargs):
    logger.debug("Replay.save(%d) : '%s'", instance.pk, instance)
    update_stats()

# automatically refresh statistics when a replay is deleted
@receiver(post_delete, sender=Replay)
def replay_del_callback(sender, instance, using, **kwargs):
    update_stats()

# automatically refresh statistics when a replay is created or modified
@receiver(post_save, sender=Comment)
def comment_save_callback(sender, instance, using, **kwargs):
    logger.debug("Comment.save(%d) : '%s'", instance.pk, instance)
    update_stats()

# automatically refresh statistics when a replay is deleted
@receiver(post_delete, sender=Comment)
def comment_del_callback(sender, instance, using, **kwargs):
    update_stats()

# automatically log creation of PlayerAccounts
@receiver(post_save, sender=PlayerAccount)
def playerAccount_save_callback(sender, instance, using, **kwargs):
    logger.debug("PlayerAccount.save(%d): accountid=%d names=%s", instance.pk, instance.accountid, instance.names)

# automatically log creation of Players
@receiver(post_save, sender=Player)
def player_save_callback(sender, instance, using, **kwargs):
    logger.debug("Player.save(%d): account=%d name=%s spectator=%s", instance.pk, instance.account.accountid, instance.name, instance.spectator)
