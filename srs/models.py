# This file is part of the "spring relay site / srs" program. It is published
# under the GPLv3.
#
# Copyright (C) 2012 Daniel Troeder (daniel #at# admin-box #dot# com)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django.db import models

class Tag(models.Model):
    name            = models.CharField(max_length=128, unique=True)

    def __unicode__(self):
        return self.name

class Map(models.Model):
    name            = models.CharField(max_length=128, unique=True)
    img_path        = models.CharField(max_length=128)
    img_url         = models.CharField(max_length=128)
    startpos        = models.CharField(max_length=512, blank=True, null = True)
    height          = models.IntegerField()
    width           = models.IntegerField()

    def __unicode__(self):
        return self.name

class Replay(models.Model):
    versionString   = models.CharField(max_length=32)
    gameID          = models.CharField(max_length=32, unique=True)
    unixTime        = models.DateTimeField()
    wallclockTime   = models.CharField(max_length=32, verbose_name='length of match')
    autohostname    = models.CharField(max_length=128, blank=True, null = True)
    gametype        = models.CharField(max_length=256)
    startpostype    = models.IntegerField(blank=True, null = True)
    title           = models.CharField(max_length=32)
    short_text      = models.CharField(max_length=36)
    long_text       = models.CharField(max_length=513)
    notcomplete     = models.BooleanField()
    rmap            = models.ForeignKey(Map)
    tags            = models.ManyToManyField(Tag)
    uploader        = models.IntegerField()
    upload_date     = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return self.title+u" :: "+self.short_text+u" :: "+self.unixTime.strftime("%Y-%m-%d")

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

class Player(models.Model):
    account         = models.ForeignKey(PlayerAccount, blank=True, null = True)
    name            = models.CharField(max_length=128)
    rank            = models.IntegerField()
    spectator       = models.BooleanField()
    team            = models.ForeignKey("Team", blank=True, null = True)
    replay          = models.ForeignKey(Replay)

    def __unicode__(self):
        return self.name

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

class ReplayFile(models.Model):
    filename        = models.CharField(max_length=256)
    path            = models.CharField(max_length=256)
    ori_filename    = models.CharField(max_length=256)
    download_count  = models.IntegerField()
    replay          = models.ForeignKey(Replay)

    def __unicode__(self):
        return self.filename[:20]

class NewsItem(models.Model):
    text            = models.CharField(max_length=256)
    post_date       = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return self.text[:50]
