# This file is part of the "spring relay site / srs" program. It is published
# under the GPLv3.
#
# Copyright (C) 2012 Daniel Troeder (daniel #at# admin-box #dot# com)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

import logging
import operator
from os.path import basename
import datetime

from django.db import models
from django.contrib.auth.models import User
from django.contrib.comments import Comment
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.db.models import Count
from django.utils import timezone

import settings

logger = logging.getLogger(__package__)

def uniqify_list(seq, idfun=None): # from http://www.peterbe.com/plog/uniqifiers-benchmark
    if idfun is None:
        def idfun(x): return x
    seen = {}
    result = []
    for item in seq:
        marker = idfun(item)
        if marker in seen: continue
        seen[marker] = 1
        result.append(item)
    return result


class Tag(models.Model):
    name            = models.CharField(max_length=128, unique=True, db_index=True)

    def __unicode__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return ('srs.views.tag', [self.name])

    @property
    def replay_count(self):
        return Replay.objects.filter(tags=self).count()

class Map(models.Model):
    name            = models.CharField(max_length=128, db_index=True)
    startpos        = models.CharField(max_length=1024, blank=True, null = True)
    height          = models.IntegerField()
    width           = models.IntegerField()

    def __unicode__(self):
        return self.name

    @models.permalink
    def get_absolute_url(self):
        return ('srs.views.rmap', [self.name])

    @property
    def replay_count(self):
        return Replay.objects.filter(map_info=self).count()

    class Meta:
        ordering = ['name']

class MapImg(models.Model):
    filename        = models.CharField(max_length=128)
    startpostype    = models.IntegerField(blank=True, null = True, verbose_name='-1 means full image')
    map_info        = models.ForeignKey(Map)

    def __unicode__(self):
        return self.map_info.name+" type:"+str(self.startpostype)

    def get_absolute_url(self):
        return (settings.STATIC_URL+"maps/"+self.filename)

class Replay(models.Model):
    versionString   = models.CharField(max_length=32)
    gameID          = models.CharField(max_length=32, unique=True, db_index=True)
    unixTime        = models.DateTimeField(verbose_name='date of match', db_index=True)
    wallclockTime   = models.CharField(max_length=32, verbose_name='length of match')
    autohostname    = models.CharField(max_length=128, blank=True, null = True, db_index=True)
    gametype        = models.CharField(max_length=256, db_index=True)
    startpostype    = models.IntegerField(blank=True, null = True)
    title           = models.CharField(max_length=256, db_index=True)
    short_text      = models.CharField(max_length=50, db_index=True)
    long_text       = models.CharField(max_length=513, db_index=True)
    notcomplete     = models.BooleanField()
    map_info        = models.ForeignKey(Map, blank=True, null = True)
    map_img         = models.ForeignKey(MapImg, blank=True, null = True)
    tags            = models.ManyToManyField(Tag)
    uploader        = models.ForeignKey(User)
    upload_date     = models.DateTimeField(auto_now_add=True, db_index=True)
    filename        = models.CharField(max_length=256)
    path            = models.CharField(max_length=256)
    download_count  = models.IntegerField(default=0)
    comment_count   = models.IntegerField(default=0)
    rated           = models.BooleanField(default=False)
    published       = models.BooleanField(default=False)

    def __unicode__(self):
        return "("+str(self.pk)+") "+self.title+" "+self.unixTime.strftime("%Y-%m-%d")

    @models.permalink
    def get_absolute_url(self):
        return ('srs.views.replay', [str(self.gameID)])

    @property
    def was_succ_uploaded(self):
        return not UploadTmp.objects.filter(replay=self).exists()

    class Meta:
        get_latest_by = 'upload_date'
        ordering = ['-upload_date']

    @property
    def game(self):
        return self.game_release.game

    @property
    def game_release(self):
        gr_name = self.gametype
        try:
            return GameRelease.objects.get(name=gr_name)
        except:
            game_name = str()
            version = str()
            in_version = False
            for gr_name_part in gr_name.split():
                version_start =  ["v", "V", "b", "("]
                version_start.extend(map(str, range(10)))
                if in_version or gr_name_part.startswith("test-")or gr_name_part.startswith("RC") or gr_name_part[0] in version_start:
                    in_version = True
                    version += gr_name_part+" "
                else:
                    game_name += gr_name_part+" "

            game_name = game_name.rstrip()
            while game_name[-1] in [" ", "-"]:
                game_name = game_name[:-1]

            version = version.rstrip()

            if version[0].upper() == "V" or version[0] == ".":
                version = version[1:]

            game, _ = Game.objects.get_or_create(name=game_name, defaults={"abbreviation": reduce(lambda x,y: x+y, [gn[0].upper() for gn in game_name.split()])})
            return GameRelease.objects.create(name=gr_name, game=game, version=version)

    @property
    def match_type(self):
        """returns string (from searching through tags): 1v1 / Team / FFA / TeamFFA'"""
        # quick and dirty using tags
        try:
            tag = self.tags.filter(name__regex=r'^[0-9]v[0-9]$')[0]
            if tag.name == "1v1":
                return "1v1"
            else:
                return "Team"
        except: pass
        try:
            tag = self.tags.get(name__regex=r'^TeamFFA$')
            return tag.name
        except: pass
        try:
            tag = self.tags.get(name__regex=r'^FFA$')
            return tag.name
        except: pass

        # thoroughly using player/team count
        allyteams = Allyteam.objects.filter(replay=self)
        if allyteams.count() == 2:
            if PlayerAccount.objects.filter(player__team__allyteam__in=allyteams).exclude(accountid=0).count() == 2:
                return "1v1"
            else:
                return "Team"
        elif allyteams.count() > 2:
            if PlayerAccount.objects.filter(player__team__allyteam__in=allyteams).exclude(accountid=0).count() == allyteams.count():
                return "FFA"
            else:
                return "TeamFFA"
        else:
            # this is kind of a broken match, but not returning anything breaks the web site
            return "1v1"

        raise Exception("Could not determine match_type for replay(%d) %s."%(self.id, self.gameID))

    @property
    def match_type_short(self):
        """returns string (from match_type()): 1 / T / F / G"""
        if self.match_type == "TeamFFA": return "G"
        else: return self.match_type[0]

    @property
    def num_players(self):
        """returns string (from counting players): 1v1 / 1v5 / 6v6 / 2v2v2v2 / ..."""
        try:
            allyteams = Allyteam.objects.filter(replay=self)
            at_sizes = [PlayerAccount.objects.filter(player__team__allyteam=at).count() for at in allyteams]
            at_sizes.sort()
            return str(reduce(lambda x,y: str(x)+"v"+str(y), at_sizes))
        except:
            return "?v?"

    @property
    def match_end(self):
        length  = self.wallclockTime.split(":")
        try:
            length2 = datetime.timedelta(seconds=int(length[2]), minutes=int(length[1]), hours=int(length[0]))
        except:
            return self.unixTime
        return self.unixTime + length2

    @property
    def duration_ISO_8601(self):
        length  = self.wallclockTime.split(":")
        try:
            return "PT"+length[0]+"H"+length[1]+"M"+length[2]+"S"
        except:
            return self.wallclockTime

    playername = "N/A" # something must exists, or PlayersReplayTable will always have an empty column
    def _playername(self, playeraccount):
        player = Player.objects.filter(replay=self, account=playeraccount)[0] # not using get() for the case of a spec-cheater
        return player.name

    def _faction_result(self, playeraccount):
        """
        Create cached entries, so this function (and the DB queries) runs only once per line in PlayersReplayTable.
        """
        try:
            player = Player.objects.get(replay=self, account=playeraccount)
            team = Team.objects.get(replay=self, teamleader=player)
            if team.allyteam.winner:
                self._result_cache = (playeraccount, "won")
            else:
                self._result_cache = (playeraccount, "lost")
            self._faction_cache = (playeraccount, team.side)
        except:
            self._result_cache = (playeraccount, "spec")
            self._faction_cache = (playeraccount, "spec")

    faction = "N/A" # something must exists, or PlayersReplayTable will always have an empty column
    def _faction(self, playeraccount):
        """
        This is used by PlayersReplayTable
        """
        if not hasattr(self, "_faction_cache") or not self._faction_cache[0] == playeraccount:
            self._faction_result(playeraccount)
        return self._faction_cache[1]

    result = "N/A" # something must exists, or PlayersReplayTable will always have an empty column
    def _result(self, playeraccount):
        """
        This is used by PlayersReplayTable
        """
        if not hasattr(self, "_result_cache") or not self._result_cache[0] == playeraccount:
            self._faction_result(playeraccount)
        return self._result_cache[1]

    @property
    def bawards(self):
        try:
            return BAwards.objects.get(replay=self)
        except:
            return None

class AdditionalReplayInfo(models.Model):
    """
    Infos that are only relevant to a few Replay objects are not worth their
    own attribute in the Replay class.
    """
    replay          = models.ForeignKey(Replay)
    key             = models.CharField(max_length=32)
    value           = models.CharField(max_length=512)

    def __unicode__(self):
        return u"%s : '%s'='%s'"%(self.replay.__unicode__(), self.key, self.value)

class Allyteam(models.Model):
    numallies       = models.IntegerField()
    startrectbottom = models.FloatField(blank=True, null = True)
    startrectleft   = models.FloatField(blank=True, null = True)
    startrectright  = models.FloatField(blank=True, null = True)
    startrecttop    = models.FloatField(blank=True, null = True)
    winner          = models.BooleanField()
    replay          = models.ForeignKey(Replay)
    num             = models.SmallIntegerField()

    def __unicode__(self):
        return str(self.id)+u" win:"+str(self.winner)

class PlayerAccount(models.Model):
    accountid       = models.IntegerField(unique=True)
    countrycode     = models.CharField(max_length=2)
    preffered_name  = models.CharField(max_length=128, db_index=True)
    sldb_privacy_mode = models.SmallIntegerField(default=1)

    def __unicode__(self):
        return str(self.accountid)+u" "+reduce(lambda x, y: x+"|"+y, self.get_names())[:40]

    @models.permalink
    def get_absolute_url(self):
        return ('srs.views.player', [self.accountid])

    @property
    def replay_count(self):
        return Player.objects.filter(account__in=self).count()
    @property
    def spectator_count(self):
        return Player.objects.filter(account__in=self, spectator=True).count()

    def get_rating(self, game, match_type):
        rating, _ = Rating.objects.get_or_create(playeraccount=self, game=game, match_type=match_type, defaults={})
        return rating

    def get_names(self):
        pls = list(Player.objects.filter(account=self).values_list("name", flat=True))
        if pls:
            try:
                pls.remove(self.preffered_name)
            except:
                pass # Player with name "pref_name"  was removed from DB, but PlayerAccount stayed
            else:
                pls.insert(0, self.preffered_name)
            return uniqify_list(pls)
        else:
            return [self.preffered_name]

    def get_all_games(self):
        gametypes = Replay.objects.filter(player__account=self, player__spectator=False).values_list("gametype", flat=True)
        return Game.objects.filter(gamerelease__name__in=uniqify_list(gametypes)).distinct()

    class Meta:
        ordering = ['accountid']


class Player(models.Model):
    account         = models.ForeignKey(PlayerAccount, blank=True, null = True)
    name            = models.CharField(max_length=128, db_index=True)
    rank            = models.SmallIntegerField()
    skill           = models.CharField(max_length=16, blank=True)
    skilluncertainty= models.SmallIntegerField(default=-1, blank=True)
    spectator       = models.BooleanField()
    team            = models.ForeignKey("Team", blank=True, null = True)
    replay          = models.ForeignKey(Replay)
    startposx       = models.FloatField(blank=True, null = True)
    startposy       = models.FloatField(blank=True, null = True)
    startposz       = models.FloatField(blank=True, null = True)

    def __unicode__(self):
        return "(%d) %s"%(self.id, self.name)

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
    num             = models.SmallIntegerField()

    def __unicode__(self):
        return "(%d) %s"%(self.pk, self.teamleader.name)

class MapModOption(models.Model):
    name            = models.CharField(max_length=128)
    value           = models.CharField(max_length=512)
    replay          = models.ForeignKey(Replay)

    def __unicode__(self):
        return self.name

#     class Meta:
#         abstract = True

class MapOption(MapModOption):
    pass

class ModOption(MapModOption):
    pass

class NewsItem(models.Model):
    text            = models.CharField(max_length=256)
    post_date       = models.DateTimeField(auto_now=True)
    show            = models.BooleanField(default=True)

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


class Game(models.Model):
    name         = models.CharField(max_length=256, db_index=True)
    abbreviation = models.CharField(max_length=64, db_index=True)
    sldb_name    = models.CharField(max_length=64, db_index=True)

    def __unicode__(self):
        return self.name[:70]+" ("+self.abbreviation+")"

    @models.permalink
    def get_absolute_url(self):
        return ('srs.views.game', [self.name])

    class Meta:
        ordering = ['name']


class GameRelease(models.Model):
    name    = models.CharField(max_length=256, db_index=True)
    version = models.CharField(max_length=64)
    game    = models.ForeignKey(Game)

    def __unicode__(self):
        return self.name[:70]+" | version: "+self.version+" | Game("+str(self.game.pk)+"): "+self.game.abbreviation

    @models.permalink
    def get_absolute_url(self):
        return ('srs.views.gamerelease', [self.name])

    class Meta:
        ordering = ['name', 'version']

class RatingBase(models.Model):
    game               = models.ForeignKey(Game)
    MATCH_TYPE_CHOICES = (('1', u'1v1'),
                           ('T', u'Team'),
                           ('F', u'FFA'),
                           ('G', u'TeamFFA'),
                           ('L', u'Global'),
                           )
    match_type         = models.CharField(max_length=1, choices=MATCH_TYPE_CHOICES, db_index=True)
    playeraccount = models.ForeignKey(PlayerAccount)
    playername    = models.CharField(max_length=128, blank=True, null=True, db_index=True) # this fields is redundant, but neccessary for db-side ordering of tables

    trueskill_mu       = models.FloatField(default=25.0)
    trueskill_sigma    = models.FloatField(default=25.0/3)

    @property
    def skilluncertainty(self):
        # from spads_0.11.9.pl - sendPlayerSkill()
        if   self.trueskill_sigma > 3  : return 3
        elif self.trueskill_sigma > 2  : return 2
        elif self.trueskill_sigma > 1.5: return 1
        else                           : return 0

    def __unicode__(self):
        return "("+str(self.id)+") "+str(self.playername)+" | "+self.game.abbreviation+" | "+self.match_type+" | "+" TS: ("+str(self.trueskill_mu)+", "+str(self.trueskill_sigma)+")"

    class Meta:
        ordering = ['-trueskill_mu']
        abstract = True

class Rating(RatingBase):
    pass

class RatingHistory(RatingBase):
    match      = models.ForeignKey(Replay)
    match_date = models.DateTimeField(blank=True, null=True, db_index=True) # this fields is redundant, but neccessary for db-side ordering of tables

    def __unicode__(self):
        return str(self.match_date)+" | "+super(RatingHistory, self).__unicode__()

    class Meta:
        ordering = ['-match_date', 'playername']

class AdditionalReplayOwner(models.Model):
    uploader         = models.ForeignKey(User)
    additional_owner = models.ForeignKey(PlayerAccount)

    def __unicode__(self):
        return u"("+unicode(self.id)+u") uploader: "+unicode(self.uploader)+u" additional_owner: "+unicode(self.additional_owner)

    class Meta:
        ordering = ['uploader__username']

class ExtraReplayMedia(models.Model):
    replay         = models.ForeignKey(Replay)
    uploader       = models.ForeignKey(User)
    upload_date    = models.DateTimeField(auto_now_add=True, db_index=True)
    comment        = models.CharField(max_length=513)
    media          = models.FileField(upload_to="media/%Y/%m/%d", blank=True)
    image          = models.ImageField(upload_to="image/%Y/%m/%d", blank=True)
    media_magic_text = models.CharField(max_length=1024, blank=True, null=True)
    media_magic_mime = models.CharField(max_length=128, blank=True, null=True)

    @property
    def media_basename(self):
        return basename(self.media.name)

    @property
    def image_basename(self):
        return basename(self.image.name)

    def __unicode__(self):
        return u"("+unicode(self.id)+u") replay: "+unicode(self.replay)+u" media: "+unicode(self.media)+u" image: "+unicode(self.image)+u" by: "+unicode(self.uploader)+u" on: "+unicode(self.upload_date)

    class Meta:
        ordering = ['-upload_date']

class SldbLeaderboardGame(models.Model):
    last_modified   = models.DateTimeField(auto_now_add=True)
    game            = models.ForeignKey(Game)
    match_type      = models.CharField(max_length=1, choices=RatingBase.MATCH_TYPE_CHOICES, db_index=True)

    def __unicode__(self):
        return u"(%d) %s | %s"%(self.id, self.game, self.match_type)

class SldbLeaderboardPlayer(models.Model):
    leaderboard     = models.ForeignKey(SldbLeaderboardGame)
    account         = models.ForeignKey(PlayerAccount)
    rank            = models.IntegerField()
    trusted_skill   = models.FloatField()
    estimated_skill = models.FloatField()
    uncertainty     = models.FloatField()
    inactivity      = models.IntegerField()

    def __unicode__(self):
        return u"(%d) %s | %d | %s | %f"%(self.id, self.leaderboard, self.rank, self.account, self.trusted_skill)

    class Meta:
        ordering = ['rank']

class SldbMatchSkillsCache(models.Model):
    last_modified   = models.DateTimeField(auto_now_add=True)
    gameID          = models.CharField(max_length=32, unique=True, db_index=True)
    text            = models.TextField()

    def __unicode__(self):
        return u"(%d) %s | %d | %s | %f"%(self.id, self.leaderboard, self.rank, self.account, self.trusted_skill)

    @staticmethod
    def purge_old():
        SldbMatchSkillsCache.objects.filter(last_modified__lt=datetime.datetime.now(tz=Replay.objects.latest().unixTime.tzinfo)-datetime.timedelta(minutes=30)).delete()

class BAwards(models.Model):
    replay            = models.ForeignKey(Replay)
    ecoKillAward1st   = models.ForeignKey(Player, blank=True, null=True, related_name="+")
    ecoKillAward2nd   = models.ForeignKey(Player, blank=True, null=True, related_name="+")
    ecoKillAward3rd   = models.ForeignKey(Player, blank=True, null=True, related_name="+")
    fightKillAward1st = models.ForeignKey(Player, blank=True, null=True, related_name="+")
    fightKillAward2nd = models.ForeignKey(Player, blank=True, null=True, related_name="+")
    fightKillAward3rd = models.ForeignKey(Player, blank=True, null=True, related_name="+")
    effKillAward1st   = models.ForeignKey(Player, blank=True, null=True, related_name="+")
    effKillAward2nd   = models.ForeignKey(Player, blank=True, null=True, related_name="+")
    effKillAward3rd   = models.ForeignKey(Player, blank=True, null=True, related_name="+")
    cowAward          = models.ForeignKey(Player, blank=True, null=True, related_name="+")
    ecoAward          = models.ForeignKey(Player, blank=True, null=True, related_name="+")
    dmgRecAward       = models.ForeignKey(Player, blank=True, null=True, related_name="+")
    sleepAward        = models.ForeignKey(Player, blank=True, null=True, related_name="+")

    def __unicode__(self):
        return u"(%d) Replay: %d | EcoKill: %s,%s,%s | FightKill: %s,%s,%s | EffKill: %s,%s,%s | Cow: %s | Eco: %s | DmgRec: %s | Sleep: %s"%(self.pk, self.replay.pk, self.ecoKillAward1st, self.ecoKillAward2nd, self.ecoKillAward3rd, self.fightKillAward1st, self.fightKillAward2nd, self.fightKillAward3rd, self.effKillAward1st, self.effKillAward2nd, self.effKillAward3rd, self.cowAward, self.ecoAward, self.dmgRecAward, self.sleepAward)

def get_owner_list(uploader):
    res = [uploader]
    res.extend(AdditionalReplayOwner.objects.filter(uploader=uploader))
    return res

def update_stats():
    """
    update only once per day
    """
    sist, created = SiteStats.objects.get_or_create(id=1, defaults={'replays': "", 'tags': "", 'maps': "", 'players': "", 'comments': ""})
    if created or (datetime.datetime.now(tz=sist.last_modified.tzinfo) - sist.last_modified).days > 0:
        # update stats
        replays  = Replay.objects.count()
        now = datetime.datetime.now(timezone.get_current_timezone())
        start_date = now - datetime.timedelta(days=30)
        tags     = Tag.objects.filter(replay__unixTime__range=(start_date, now)).annotate(num_replay=Count('replay')).order_by('-num_replay')[:20]
        maps     = Map.objects.filter(replay__unixTime__range=(start_date, now)).annotate(num_replay=Count('replay')).order_by('-num_replay')[:20]
        tp = list()

        # This takes an insane amount of time. It is the reason stats are updated only once per day.
        for pa in PlayerAccount.objects.exclude(accountid=0).order_by("accountid"): # exclude bots
            nummatches =  Player.objects.filter(account=pa, spectator=False, replay__unixTime__range=(start_date, now)).count()
            tp.append((nummatches, pa))
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

        sist.replays = replays
        sist.tags = tags_s
        sist.maps = maps_s
        sist.players = players_s
        sist.comments = comments_s
        sist.save()

# TODO: use a proxy model for this
User.get_absolute_url = lambda self: "/user/"+str(self.get_profile().accountid)+"/"
User.replays_uploaded = lambda self: Replay.objects.filter(uploader=self).count()

# TODO: use a proxy model for this
Comment.replay = lambda self: self.content_object.__unicode__()
Comment.comment_short = lambda self: self.comment[:50]+"..."

# HEAVY DEBUG
# automatically log each DB object save
#@receiver(post_save)
#def obj_save_callback(sender, instance, **kwargs):
#    # Session obj has u'str encoded hex key as pk
#    logger.debug("%s.save(%s) : '%s'", instance.__class__.__name__, instance.pk, instance)

# automatically log each DB object delete
#@receiver(post_delete)
#def obj_del_callback(sender, instance, **kwargs):
#    # Session obj has u'str encoded hex key as pk
#    logger.debug("%s.delete(%s) : '%s'", instance.__class__.__name__, instance.pk, instance)

# automatically refresh statistics when a replay is created or modified
@receiver(post_save, sender=Replay)
def replay_save_callback(sender, instance, **kwargs):
    logger.debug("Replay.save(%d) : '%s'", instance.pk, instance)
    # check for new new Game[Release] object
    if kwargs["created"]: instance.game_release
    update_stats()

# automatically refresh statistics when a replay is deleted
@receiver(post_delete, sender=Replay)
def replay_del_callback(sender, instance, **kwargs):
    update_stats()

# automatically refresh statistics when a replay is created or modified
@receiver(post_save, sender=Comment)
def comment_save_callback(sender, instance, **kwargs):
    logger.debug("Comment.save(%d) : '%s'", instance.pk, instance)
    update_stats()

# automatically refresh statistics when a replay is deleted
@receiver(post_delete, sender=Comment)
def comment_del_callback(sender, instance, **kwargs):
    update_stats()

# automatically log creation of PlayerAccounts
@receiver(post_save, sender=PlayerAccount)
def playerAccount_save_callback(sender, instance, **kwargs):
    logger.debug("PlayerAccount.save(%d): accountid=%d preffered_name=%s", instance.pk, instance.accountid, instance.preffered_name)
