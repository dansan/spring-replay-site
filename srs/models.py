# This file is part of the "spring relay site / srs" program. It is published
# under the GPLv3.
#
# Copyright (C) 2012 Daniel Troeder (daniel #at# admin-box #dot# com)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django.db import models
from django.contrib.auth.models import User
from django.contrib.comments import Comment
from django.contrib.contenttypes.models import ContentType
import settings

class Tag(models.Model):
    name            = models.CharField(max_length=128, unique=True)

    def __unicode__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return ('srs.views.tag', [self.name])

    def replay_count(self):
        return Replay.objects.filter(tags__name__contains=self.name).count()

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

    def replay_count(self):
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
    unixTime        = models.DateTimeField()
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
    upload_date     = models.DateTimeField(auto_now=True)
    replayfile      = models.ForeignKey(ReplayFile)
    def __unicode__(self):
        return self.title+" "+self.unixTime.strftime("%Y-%m-%d")

    @models.permalink
    def get_absolute_url(self):
        return ('srs.views.replay', [str(self.gameID)])

    def comment_count(self):
        r_t = ContentType.objects.get_for_model(Replay)
        return Comment.objects.filter(object_pk=str(self.pk), content_type=r_t.pk).count()

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
        return str(self.accountid)+u" "+self.names[:10]

    def replay_count(self):
        return Player.objects.filter(account=self).count()

    def spectator_count(self):
        return Player.objects.filter(account=self, spectator=True).count()

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
        return unicode(self.allyteam)+u" "+self.side

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

User.get_absolute_url = lambda self: "/user/"+self.username+"/"
User.replay_count = lambda self: Replay.objects.filter(uploader=self).count()
Comment.replay = lambda self: self.content_object.__unicode__()
Comment.comment_short = lambda self: self.comment[:50]+"..."
