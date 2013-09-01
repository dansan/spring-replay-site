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

from django.db import models
from django.contrib.auth.models import User
from django.contrib.comments import Comment
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.db.models import Count

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

    def __unicode__(self):
        return "("+str(self.pk)+") "+self.title+" "+self.unixTime.strftime("%Y-%m-%d")

    @models.permalink
    def get_absolute_url(self):
        return ('srs.views.replay', [str(self.gameID)])

    def was_succ_uploaded(self):
        return not UploadTmp.objects.filter(replay=self).exists()

    class Meta:
        get_latest_by = 'upload_date'
        ordering = ['-upload_date']

    def game_release(self):
        gr_name = self.gametype
        try:
            return GameRelease.objects.get(name=gr_name)
        except:
            game_name = str()
            version = str()
            in_version = False
            for gr_name_part in gr_name.split():
                version_start =  ["v", "V", "b"]
                version_start.extend(map(str, range(10)))
                if in_version or gr_name_part.startswith("test-") or gr_name_part[0] in version_start:
                    in_version = True
                    version += gr_name_part+" "
                else:
                    game_name += gr_name_part+" "

            game_name = game_name.rstrip()
            version = version.rstrip()

            if version[0].upper() == "V" or version[0] == ".":
                version = version[1:]

            game, _ = Game.objects.get_or_create(name__startswith=game_name, defaults={"name": game_name, "abbreviation": reduce(lambda x,y: x+y, [gn[0].upper() for gn in game_name.split()])})
            return GameRelease.objects.create(name=gr_name, game=game, version=version)

    def match_type(self):
        """returns string (from searching through tags): 1v1 / Team / FFA / TeamFFA / '1v1 BA Tourney'"""
        # quick and dirty using tags
        try:
            tag = self.tags.filter(name__regex=r'^[0-9]v[0-9]$')[0]
            if tag.name == "1v1":
                if self.tags.filter(name="Tourney").exists() and self.game_release().game.name == "Balanced Annihilation":
                    return "1v1 BA Tourney"
                else:
                    return tag.name # "1v1"
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

    def match_type_short(self, ba1v1tourney=False):
        """returns string (from match_type()): 1 / T / F / G / O"""
        if self.match_type() == "TeamFFA": return "G"
        elif ba1v1tourney and self.match_type() == "1v1 BA Tourney": return "O" # return "O" only if a manual rating.rate_match() is run with ba1v1tourney=True
        else: return self.match_type()[0]

    def num_players(self):
        """returns string (from counting players): 1v1 / 1v5 / 6v6 / 2v2v2v2 / ..."""
        try:
            allyteams = Allyteam.objects.filter(replay=self)
            at_sizes = [PlayerAccount.objects.filter(player__team__allyteam=at).count() for at in allyteams]
            at_sizes.sort()
            return str(reduce(lambda x,y: str(x)+"v"+str(y), at_sizes))
        except:
            return "?v?"

class Allyteam(models.Model):
    numallies       = models.IntegerField()
    startrectbottom = models.FloatField(blank=True, null = True)
    startrectleft   = models.FloatField(blank=True, null = True)
    startrectright  = models.FloatField(blank=True, null = True)
    startrecttop    = models.FloatField(blank=True, null = True)
    winner          = models.BooleanField()
    replay          = models.ForeignKey(Replay)

    def __unicode__(self):
        return str(self.id)+u" win:"+str(self.winner)

class PlayerAccount(models.Model):
    accountid       = models.IntegerField(unique=True)
    countrycode     = models.CharField(max_length=2)
    preffered_name  = models.CharField(max_length=128, db_index=True)
    primary_account = models.ForeignKey("self", blank=True, null = True)

    def __unicode__(self):
        return str(self.accountid)+u" "+reduce(lambda x, y: x+"|"+y, self.get_names())[:40]

    @models.permalink
    def get_absolute_url(self):
        return ('srs.views.player', [self.accountid])

    def replay_count(self):
        return Player.objects.filter(account__in=self.get_all_accounts()).count()
    def spectator_count(self):
        return Player.objects.filter(account__in=self.get_all_accounts(), spectator=True).count()

    def get_rating(self, game, match_type):
        rating, _ = Rating.objects.get_or_create(playeraccount=self.get_primary_account(), game=game, match_type=match_type, defaults={"playeraccount": self.get_primary_account(), "game": game, "match_type": match_type})
        return rating

    def get_primary_account(self):
        if self.primary_account == None:
            return self
        else:
            return self.primary_account.get_primary_account()

    def get_all_accounts(self):
        accounts = [self.get_primary_account()]
        accounts.extend(PlayerAccount.objects.filter(primary_account=self.get_primary_account()).order_by("accountid"))
        accounts.extend(PlayerAccount.objects.filter(primary_account__in=accounts).exclude(primary_account=self.get_primary_account()).order_by("accountid"))
        return accounts

    def get_names(self):
        pls = [p[0] for p in Player.objects.filter(account=self).values_list("name")]
        if pls:
            return uniqify_list(pls)
        else:
            return [self.preffered_name]

    def get_all_names(self):
        pref_name = self.get_all_accounts()[0].preffered_name
        names = str()
        namelist = list()

        for pa in self.get_all_accounts():
            namelist.extend(pa.get_names())
        uniqify_list(namelist)
        try:
            namelist.remove(pref_name)
        except:
            pass # Player with name "pref_name"  was removed from DB, but PlayerAccount stayed
        namelist.insert(0, pref_name)
        names += reduce(lambda x, y: x+" "+y, namelist)
        return names.rstrip()

    def get_preffered_name(self):
        return self.get_primary_account().preffered_name

    class Meta:
        ordering = ['accountid']


class Player(models.Model):
    account         = models.ForeignKey(PlayerAccount, blank=True, null = True)
    name            = models.CharField(max_length=128, db_index=True)
    rank            = models.IntegerField()
    skill           = models.CharField(max_length=16, blank=True)
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

    def __unicode__(self):
        return self.name[:70]+" ("+self.abbreviation+")"

    @models.permalink
    def get_absolute_url(self):
        return ('srs.views.game', [self.name])

    class Meta:
        ordering = ['name']


class GameRelease(models.Model):
    name    = models.CharField(max_length=256)
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
                           ('O', u'BA 1v1 Tourney'),
                           )
    match_type         = models.CharField(max_length=1, choices=MATCH_TYPE_CHOICES, db_index=True)
    playeraccount = models.ForeignKey(PlayerAccount)
    # this fields is really redundant, but neccessary for db-side ordering of tables
    playername    = models.CharField(max_length=128, blank=True, null=True, db_index=True)

    elo                = models.FloatField(default=1500.0)
    elo_k              = models.FloatField(default=30.0)
    glicko             = models.FloatField(default=1500.0)
    glicko_rd          = models.FloatField(default=350.0)
    glicko_last_period = models.DateTimeField(auto_now_add=True, blank=True, null = True)
    trueskill_mu       = models.FloatField(default=25.0)
    trueskill_sigma    = models.FloatField(default=25.0/3)

    def set_elo(self, elo_rating):
        self.elo = elo_rating.mean
        self.elo_k = elo_rating.k_factor
        self.save()

    def set_glicko(self, glicko_rating):
        self.glicko = glicko_rating.mean
        self.glicko_rd = min(glicko_rating.stdev, 50) # never drop RD < 50, to allow for improvements for regular players
        self.glicko_last_period = glicko_rating.last_rating_period
        self.save()

    def set_trueskill(self, trueskill_rating):
        self.trueskill_mu = trueskill_rating.mean
        self.trueskill_sigma = trueskill_rating.stdev
        self.save()

    def __unicode__(self):
        return "("+str(self.id)+") "+str(self.playername)+" | "+self.game.abbreviation+" | "+self.match_type+" | "+"elo:("+str(self.elo)+", "+str(self.elo_k)+") glicko:("+str(self.glicko)+", "+str(self.glicko_rd)+") trueskill: ("+str(self.trueskill_mu)+", "+str(self.trueskill_sigma)+")"

    class Meta:
        ordering = ['-elo', '-glicko', '-trueskill_mu']
#        abstract = True # damn... forgot this, and now I cannot add it without puging the whole table

class Rating(RatingBase):
    pass

class RatingHistory(RatingBase):
    match         = models.ForeignKey(Replay)

    # this fields is really redundant, but neccessary for db-side ordering of tables
    match_date    = models.DateTimeField(blank=True, null=True, db_index=True)
    ALGO_CHOICES  = (('E', u'ELO'),
                     ('G', u'Glicko'),
                     ('B', u'ELO & Glicko'),
                     ('T', u'Trueskill'),
                     ('A', u'ELO, Glicko & Trueskill'),
                     ('C', u'Creation'),
                     )
    algo_change   = models.CharField(max_length=1, choices=ALGO_CHOICES, default="C")

    def set_elo(self, elo_rating):
        super(RatingHistory, self).set_elo(elo_rating)
        self.algo_change = "E"
        self.save()

    def set_glicko(self, glicko_rating):
        super(RatingHistory, self).set_glicko(glicko_rating)
        self.algo_change = "G"
        self.save()

    def set_trueskill(self, trueskill_rating):
        super(RatingHistory, self).set_trueskill(trueskill_rating)
        self.algo_change = "T"
        self.save()

    def __unicode__(self):
        return str(self.match_date)+" | "+super(RatingHistory, self).__unicode__()

    def set_sorting_data(self):
        self.playername = self.playeraccount.preffered_name
        self.match_date = self.match.unixTime
        self.save()

    class Meta:
        ordering = ['-match_date', 'playername']

class RatingAdjustmentHistory(RatingBase):
    change_date   = models.DateTimeField(auto_now=True, db_index=True)
    ALGO_CHOICES  = (('E', u'ELO'),
                     ('G', u'Glicko'),
                     ('T', u'Trueskill'),
                     )
    algo_change   = models.CharField(max_length=1, choices=ALGO_CHOICES, default="T")
    admin         = models.ForeignKey(PlayerAccount, related_name='ratingAdjustmentAdmin')

    def __unicode__(self):
        if   self.algo_change == "E": change = self.elo
        elif self.algo_change == "G": change = self.glicko
        elif self.algo_change == "T": change = self.trueskill_mu
        else: raise Exception("This should not happen.")
        return "("+str(self.id)+") "+str(self.change_date)+" | '"+self.admin.get_preffered_name()+"' changed '"+self.playeraccount.get_preffered_name()+"' | "+self.game.abbreviation+" | "+self.algo_change+" | "+str(change)

    class Meta:
        ordering = ['-change_date']


class RatingQueue(models.Model):
    """used during long running initial_rating()"""
    replay = models.ForeignKey(Replay)


class AccountUnificationLog(models.Model):
    change_date   = models.DateTimeField(auto_now_add=True, db_index=True)
    admin         = models.ForeignKey(PlayerAccount, related_name='accountUnificationAdmin')
    account1      = models.ForeignKey(PlayerAccount, related_name='accountUnificationAccount1')
    account2      = models.ForeignKey(PlayerAccount, related_name='accountUnificationAccount2')
    all_accounts  = models.CharField(max_length=512)
    reverted      = models.BooleanField(default=False)

    def __unicode__(self):
        return "("+str(self.id)+") "+str(self.change_date)+" | '"+self.admin.get_preffered_name()+"' unified '"+self.account1.preffered_name+"'("+str(self.account1.accountid)+") and '"+self.account2.preffered_name+"'("+str(self.account2.accountid)+")"

    @models.permalink
    def get_absolute_url(self):
        return ('srs.views.account_unification_history', [])

    class Meta:
        ordering = ['-change_date']

class AccountUnificationRatingBackup(RatingBase):
    account_unification_log = models.ForeignKey(AccountUnificationLog)

    def __unicode__(self):
        return str(self.account_unification_log.change_date)+" | "+super(AccountUnificationRatingBackup, self).__unicode__()

class AccountUnificationBlocking(models.Model):
    account1      = models.ForeignKey(PlayerAccount, related_name='accountUnificationBlockingAccount1')
    account2      = models.ForeignKey(PlayerAccount, related_name='accountUnificationBlockingAccount2')

    def __unicode__(self):
        return str(self.account_unification_log.change_date)+" | "+super(AccountUnificationRatingBackup, self).__unicode__()

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

    def media_basename(self):
        return basename(self.media.name)

    def image_basename(self):
        return basename(self.image.name)

    def __unicode__(self):
        return u"("+unicode(self.id)+u") replay: "+unicode(self.replay)+u" media: "+unicode(self.media)+u" image: "+unicode(self.image)+u" by: "+unicode(self.uploader)+u" on: "+unicode(self.upload_date)

    class Meta:
        ordering = ['-upload_date']

def get_owner_list(uploader):
    res = [uploader]
    res.extend(AdditionalReplayOwner.objects.filter(uploader=uploader))
    return res

def update_stats():
    replays  = Replay.objects.count()
    tags     = Tag.objects.annotate(num_replay=Count('replay')).order_by('-num_replay')[:20]
    maps     = Map.objects.annotate(num_replay=Count('replay')).order_by('-num_replay')[:20]
    tp = list()

    for pa in PlayerAccount.objects.filter(primary_account__isnull=True).exclude(accountid=0).order_by("accountid"): # exclude bots
        nummatches =  Player.objects.filter(account__in=pa.get_all_accounts(), spectator=False).count()
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
    if kwargs["created"]: instance.game_release()
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

# set sorting info when a RatingHistory is saved
@receiver(post_save, sender=RatingHistory)
def ratinghistory_save_callback(sender, instance, **kwargs):
    # check for new new Game[Release] object
    if kwargs["created"]: instance.set_sorting_data()

# set sorting info when a RatingHistory is saved
@receiver(post_save, sender=Rating)
def rating_save_callback(sender, instance, **kwargs):
    # check for new new Game[Release] object
    if kwargs["created"]:
        instance.playername = instance.playeraccount.preffered_name
        instance.save()
