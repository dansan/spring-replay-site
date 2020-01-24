# This file is part of the "spring relay site / srs" program. It is published
# under the GPLv3.
#
# Copyright (C) 2016-2020 Daniel Troeder (daniel #at# admin-box #dot# com)
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import logging
import operator
from os.path import basename
import datetime
import os
import zlib
from collections import defaultdict, Counter, OrderedDict
from functools import reduce

from django.db import models
from django.contrib.auth.models import User
from django_comments.models import Comment
from django.db.models.signals import post_delete, post_save
from django.db.models.deletion import CASCADE
from django.dispatch import receiver
from django.db.models import Count
from django.urls import reverse
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.conf import settings
from background_task import background
import ujson

from srs.mail import send_mail

from infolog_upload.notifications import Notifications

logger = logging.getLogger(__name__)


def uniqify_list(seq, idfun=None):  # from http://www.peterbe.com/plog/uniqifiers-benchmark
    if idfun is None:
        def idfun(x):
            return x
    seen = {}
    result = []
    for item in seq:
        marker = idfun(item)
        if marker in seen:
            continue
        seen[marker] = 1
        result.append(item)
    return result


class JSONTextField(models.TextField):
    def from_db_value(self, value, expression, connection, context):
        if not value:
            return None
        return self.to_python(value)

    def get_prep_value(self, value):
        if isinstance(value, dict):
            try:
                del value["torrent"]
            except KeyError:
                pass
            try:
                value["timestamp"] = value["timestamp"].value
            except KeyError:
                pass
        return ujson.dumps(value)

    def to_python(self, value):
        if isinstance(value, dict) or value is None:
            return value
        res = ujson.loads(value)
        if isinstance(res, dict) and "timestamp" in res:
            res["timestamp"] = datetime.datetime.strptime(res["timestamp"], "%Y%m%dT%H:%M:%S")
        return res

    def value_to_string(self, obj):
        value = self.value_from_object(obj)
        return self.get_prep_value(value)


class Tag(models.Model):
    name = models.CharField(max_length=128, unique=True)

    def __repr__(self):
        return "Tag({}, {})".format(self.pk, self.name)

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('srs/tag', args=[self.name])

    @property
    def replay_count(self):
        return Replay.objects.filter(tags=self).count()


class Map(models.Model):
    name = models.CharField(max_length=128, db_index=True)
    startpos = models.CharField(max_length=1024, blank=True, null=True)
    height = models.IntegerField()
    width = models.IntegerField()
    metadata2 = JSONTextField(blank=True, null=True, default=None)

    def __repr__(self):
        return "Map({}, {})".format(self.pk, self.name)

    def __unicode__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('srs/rmap', args=[self.name])

    @property
    def replay_count(self):
        return Replay.objects.filter(map_info=self).count()

    class Meta:
        ordering = ['name']


class MapImg(models.Model):
    filename = models.CharField(max_length=128)
    startpostype = models.IntegerField(blank=True, null=True, verbose_name='-1 means full image')
    map_info = models.ForeignKey(Map, on_delete=CASCADE)

    def __unicode__(self):
        return "MapImg({}, {}, {})".format(self.pk, self.map_info.name, self.startpostype)

    def get_absolute_url(self):
        return "{}maps/{}".format(settings.STATIC_URL, self.filename)


class Replay(models.Model):
    versionString = models.CharField(max_length=128)
    gameID = models.CharField(max_length=32, unique=True)
    unixTime = models.DateTimeField(verbose_name='date of match', db_index=True)
    wallclockTime = models.CharField(max_length=32, verbose_name='length of match')
    autohostname = models.CharField(max_length=128, blank=True, null=True, db_index=True)
    gametype = models.CharField(max_length=256, db_index=True)
    startpostype = models.IntegerField(blank=True, null=True)
    title = models.CharField(max_length=256, db_index=True)
    short_text = models.CharField(max_length=50, db_index=True)
    long_text = models.CharField(max_length=513, db_index=True)
    notcomplete = models.BooleanField(default=True)
    map_info = models.ForeignKey(Map, blank=True, null=True, on_delete=CASCADE)
    map_img = models.ForeignKey(MapImg, blank=True, null=True, on_delete=CASCADE)
    tags = models.ManyToManyField(Tag)
    uploader = models.ForeignKey(User, on_delete=CASCADE)
    upload_date = models.DateTimeField(auto_now_add=True, db_index=True)
    filename = models.CharField(max_length=256)
    path = models.CharField(max_length=256)
    download_count = models.IntegerField(default=0)
    comment_count = models.IntegerField(default=0)
    rated = models.BooleanField(default=False)
    published = models.BooleanField(default=False)

    def __unicode__(self):
        return "Replay({}, {!r}, {!r})".format(self.pk, self.gameID, self.title)

    def to_dict(self):
        return {"id": self.id,
                "versionString": self.versionString,
                "gameID": self.gameID,
                "unixTime": self.unixTime,
                "wallclockTime": self.wallclockTime,
                "autohostname": self.autohostname,
                "gametype": self.gametype,
                "startpostype": self.startpostype,
                "title": self.title,
                "short_text": self.short_text,
                "long_text": self.long_text,
                "map_name": self.map_info.name,
                "map_startpos": self.map_info.startpos,
                "map_width": self.map_info.width,
                "map_height": self.map_info.height,
                "tags": ",".join(self.tags.all().values_list("name", flat=True)) if self.tags.exists() else "",
                "uploader": self.uploader.username,
                "upload_date": self.upload_date}

    def get_absolute_url(self):
        return reverse('srs/replay', args=[str(self.gameID)])

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
        try:
            gr = GameRelease.objects.get(name=self.gametype)
            return gr
        except ObjectDoesNotExist:
            # new game release
            pass

        # look for existing game name
        game = None
        for i in range(len(self.gametype)):
            _game = Game.objects.filter(name=self.gametype[:-1 * i])
            if _game.count() == 1:
                game = _game.first()
                break
            elif _game.count() > 1:
                msg = "Found %r Games with name %r: %r.\ngametype: %r\ngameID: %r\nmatch: %r." % (_game.count(),
                                                                                                  self.gametype[
                                                                                                  :-1 * i],
                                                                                                  _game, self.gametype,
                                                                                                  self.gameID,
                                                                                                  self.__unicode__())
                logger.error(msg)
                send_mail([x[1] for x in settings.ADMINS], "SRS: ambiguous game name", msg)
            else:
                pass
        if not game:
            logger.debug("not game")
            msg = "Unknown gametype: %r\ngameID: %r\nmatch: %r." % (self.gametype, self.gameID, self.__unicode__())
            logger.error(msg)
            send_mail([x[1] for x in settings.ADMINS], "SRS: Unknown game name", msg)

            game_name = str()
            version = str()
            in_version = False
            for gr_name_part in self.gametype.split():
                version_start = ["v", "V", "b", "("]
                version_start.extend(map(str, range(10)))
                if in_version or gr_name_part.upper().startswith("TEST") or gr_name_part.upper().startswith("RC") or \
                                gr_name_part[0] in version_start:
                    in_version = True
                    version += "{} ".format(gr_name_part)
                else:
                    game_name += "{} ".format(gr_name_part)

            game_name = game_name.rstrip()
            while game_name[-1] in [" ", "-"]:
                game_name = game_name[:-1]
        else:
            game_name = game.name
            version = self.gametype[len(game.name):]
        version = version.strip()
        if not version:
            version = "n/a"

        if version[0].upper() == "V" or version[0] == ".":
            version = version[1:]

        game, _ = Game.objects.get_or_create(name=game_name, defaults={
            "abbreviation": reduce(lambda x, y: x + y, [gn[0].upper() for gn in game_name.split()])})
        return GameRelease.objects.create(name=self.gametype, game=game, version=version)

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
        except IndexError:
            pass
        try:
            tag = self.tags.get(name__regex=r'^TeamFFA$')
            return tag.name
        except ObjectDoesNotExist:
            pass
        try:
            tag = self.tags.get(name__regex=r'^FFA$')
            return tag.name
        except ObjectDoesNotExist:
            pass

        # thoroughly using player/team count
        allyteams = Allyteam.objects.filter(replay=self)
        if allyteams.count() == 2:
            if PlayerAccount.objects.filter(player__team__allyteam__in=allyteams).exclude(accountid=0).count() == 2:
                return "1v1"
            else:
                return "Team"
        elif allyteams.count() > 2:
            if PlayerAccount.objects.filter(player__team__allyteam__in=allyteams).exclude(
                    accountid=0).count() == allyteams.count():
                return "FFA"
            else:
                return "TeamFFA"
        else:
            # this is kind of a broken match, but not returning anything breaks the web site
            return "1v1"

    @property
    def match_type_short(self):
        """returns string (from match_type()): 1 / T / F / G"""
        if self.match_type == "TeamFFA":
            return "G"
        else:
            return self.match_type[0]

    @property
    def num_players(self):
        """returns string (from counting players): 1v1 / 1v5 / 6v6 / 2v2v2v2 / ..."""
        try:
            allyteams = Allyteam.objects.filter(replay=self)
            at_sizes = [PlayerAccount.objects.filter(player__team__allyteam=at).count() for at in allyteams]
            at_sizes.sort()
            return str(reduce(lambda x, y: "{}v{}".format(x, y), at_sizes))
        except:
            logger.exception("FIXME: to broad exception handling.")
            return "?v?"

    @property
    def match_end(self):
        length = self.wallclockTime.split(":")
        try:
            length2 = datetime.timedelta(seconds=int(length[2]), minutes=int(length[1]), hours=int(length[0]))
        except KeyError:
            return self.unixTime
        return self.unixTime + length2

    @property
    def duration_ISO_8601(self):
        length = self.wallclockTime.split(":")
        try:
            return "PT{0}H{1}M{2}S".format(*length)
        except IndexError:
            return self.wallclockTime

    playername = "N/A"  # something must exists, or PlayersReplayTable will always have an empty column

    def _playername(self, playeraccount):
        player = Player.objects.filter(replay=self, account=playeraccount)[
            0]  # not using get() for the case of a spec-cheater
        return player.name

    def _faction_result(self, playeraccount):
        """
        Create cached entries, so this function (and the DB queries) runs only once per line in PlayersReplayTable.
        """
        try:
            player = Player.objects.get(replay=self, account=playeraccount)
        except MultipleObjectsReturned:  # happens on Bots player page
            if playeraccount.accountid == 0:
                player = Player.objects.filter(replay=self, account=playeraccount)[0]
            else:
                player = Player.objects.get(replay=self, account=playeraccount, spectator=False)
        try:
            team = Team.objects.filter(replay=self, teamleader=player)[0]
            if team.allyteam.winner:
                self._result_cache = (playeraccount, "won")
            else:
                self._result_cache = (playeraccount, "lost")
            self._faction_cache = (playeraccount, team.side)
        except (ObjectDoesNotExist, IndexError):
            self._result_cache = (playeraccount, "spec")
            self._faction_cache = (playeraccount, "spec")

    faction = "N/A"  # something must exists, or PlayersReplayTable will always have an empty column

    def _faction(self, playeraccount):
        """
        This is used by PlayersReplayTable
        """
        if not hasattr(self, "_faction_cache") or not self._faction_cache[0] == playeraccount:
            self._faction_result(playeraccount)
        return self._faction_cache[1]

    result = "N/A"  # something must exists, or PlayersReplayTable will always have an empty column

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
        except ObjectDoesNotExist:
            return None

    @property
    def cursed_awards(self):
        """
        :return: [('shell', {
            'players': [(<Player a>, 12), (<Player b>, 34)],
            'img': 'trophy_shell.png',
            'name': 'Turtle Shell'
            }),
        ...]
        """
        res = dict()
        ca_fields = CursedAwards.sorted_field_names()
        try:
            for ca in CursedAwards.objects.filter(replay=self):
                for fn in ca_fields:
                    cav = getattr(ca, fn)
                    if cav:
                        res.setdefault(fn, {})['name'] = CursedAwards.field_to_name[fn]
                        res[fn]['img'] = os.path.join('img/cursed_awards', CursedAwards.field_to_image[fn])
                        res[fn].setdefault('players', []).append((ca.player, cav))
                        if len(res[fn]['players']) > 1:
                            res[fn]['players'] = sorted(res[fn]['players'], key=operator.itemgetter(1), reverse=True)
        except ObjectDoesNotExist:
            return None
        return sorted(res.items(), key=operator.itemgetter(0))


class PlayerStats(models.Model):
    replay = models.ForeignKey(Replay, on_delete=CASCADE)
    stats = models.BinaryField(blank=True, null=True, default=None)

    @property
    def decompressed(self):
        return ujson.loads(zlib.decompress(self.stats))

    def __unicode__(self):
        return u'PlayerStats(pk={}, replay.pk={}, {!r}...)'.format(self.pk, self.replay.pk, self.stats[:4])


class TeamStats(models.Model):
    replay = models.ForeignKey(Replay, on_delete=CASCADE)
    stat_type = models.CharField(max_length=32)
    stats = models.BinaryField(blank=True, null=True, default=None)

    graphid2label = OrderedDict((
        ('metalUsed', 'Metal Used'),
        ('metalProduced', 'Metal Produced'),
        ('metalExcess', 'Metal Excess'),
        ('metalReceived', 'Metal Received'),
        ('metalSent', 'Metal Sent'),
        ('energyUsed', 'Energy Used'),
        ('energyProduced', 'Energy Produced'),
        ('energyExcess', 'Energy Excess'),
        ('energyReceived', 'Energy Received'),
        ('energySent', 'Energy Sent'),
        ('damageDealt', 'Damage Dealt'),
        ('damageReceived', 'Damage Received'),
        ('unitsProduced', 'Units Produced'),
        ('unitsKilled', 'Units Killed'),
        ('unitsDied', 'Units Died'),
        ('unitsReceived', 'Units Received'),
        ('unitsSent', 'Units Sent'),
        ('unitsCaptured', 'Units Captured'),
        ('unitsOutCaptured', 'Units Stolen'),
    ))

    @property
    def decompressed(self):
        return ujson.loads(zlib.decompress(self.stats))

    @property
    def label(self):
        return self.graphid2label[self.stat_type]

    def __unicode__(self):
        return u'TeamStats(pk={}, replay.pk={}, stat_type={}, {!r}...)'.format(self.pk, self.replay.pk, self.stat_type, self.stats[:4])


class AdditionalReplayInfo(models.Model):
    """
    Infos that are only relevant to a few Replay objects are not worth their
    own attribute in the Replay class.
    """
    replay = models.ForeignKey(Replay, on_delete=CASCADE)
    key = models.CharField(max_length=32)
    value = models.CharField(max_length=512)

    def __unicode__(self):
        return u"AdditionalReplayInfo({}, {}): '{}'='{}'".format(self.pk, self.replay, self.key, self.value)


class Allyteam(models.Model):
    numallies = models.IntegerField()
    startrectbottom = models.FloatField(blank=True, null=True)
    startrectleft = models.FloatField(blank=True, null=True)
    startrectright = models.FloatField(blank=True, null=True)
    startrecttop = models.FloatField(blank=True, null=True)
    winner = models.BooleanField(default=False)
    replay = models.ForeignKey(Replay, on_delete=CASCADE)
    num = models.SmallIntegerField()

    def __unicode__(self):
        return u"Allyteam({}) win:{}".format(self.id, self.winner)


class PlayerAccount(models.Model):
    accountid = models.IntegerField(unique=True)
    countrycode = models.CharField(max_length=2)
    preffered_name = models.CharField(max_length=128, db_index=True)
    sldb_privacy_mode = models.SmallIntegerField(default=1)

    def __unicode__(self):
        return u"PlayerAccount({}: {})".format(self.accountid, reduce(lambda x, y: "{}|{}".format(x, y), self.get_names())[:40])

    def get_absolute_url(self):
        return reverse('srs/player', args=[self.accountid])

    @property
    def replay_count(self):
        return Player.objects.filter(account__in=self).count()

    @property
    def spectator_count(self):
        return Player.objects.filter(account__in=self, spectator=True).count()

    def get_rating(self, game, match_type):
        try:
            rating, _ = Rating.objects.get_or_create(playeraccount=self, game=game, match_type=match_type)
            return rating
        except MultipleObjectsReturned:
            # this shouldn't happen, was a bug, now delete last object and return first
            ratings = Rating.objects.filter(playeraccount=self, game=game, match_type=match_type)
            ratings.last().delete()
            return ratings.first()

    def get_names(self):
        pls = list(Player.objects.filter(account=self).values_list("name", flat=True))
        if pls:
            try:
                pls.remove(self.preffered_name)
            except ValueError:
                pass  # Player with name "pref_name"  was removed from DB, but PlayerAccount stayed
            else:
                pls.insert(0, self.preffered_name)
            return uniqify_list(pls)
        else:
            return [self.preffered_name]

    def get_all_games(self):
        gametypes = Replay.objects.filter(player__account=self, player__spectator=False).values_list("gametype",
                                                                                                     flat=True)
        return Game.objects.filter(gamerelease__name__in=uniqify_list(gametypes)).distinct()

    def get_all_games_no_bots(self):
        gametypes = Replay.objects.filter(player__account=self, player__spectator=False).exclude(
            tags=Tag.objects.get(name="Bot")).values_list("gametype", flat=True)
        return Game.objects.filter(gamerelease__name__in=uniqify_list(gametypes)).distinct()

    def get_user(self):
        try:
            return User.objects.get(userprofile__accountid=self.accountid)
        except ObjectDoesNotExist:
            return None

    @property
    def bawards(self):
        """
        Find number of won BA awards (for all award types).

        :return: dict: {'cowAward': 0, 'dmgRecAward': 2, 'ecoAward': 3, ...}
        """
        res = dict()
        field_names = [field.name for field in BAwards._meta.get_fields() if "Award" in field.name and "Score" not in field.name]
        for award in field_names:
            kwargs = {"{}__account".format(award): self}
            res[award] = BAwards.objects.filter(**kwargs).count()
        return res

    @property
    def xtawards(self):
        """
        Find top 10 hero and "lost in service" units for this player. Sorted by headcount.

        :return: tuple: heroes, lost. each is a list of tuples: ([(u'Sumo', 9), (u'Light Laser Tower', 8), ...], [(), ..])
        """
        awards = XTAwards.objects.filter(player__account=self, isAlive=1).values_list("unit", flat=True)
        co = Counter(awards)
        heroes = co.most_common(10)
        awards = XTAwards.objects.filter(player__account=self, isAlive=0).values_list("unit", flat=True)
        co = Counter(awards)
        lost = co.most_common(10)
        return heroes, lost

    @property
    def cursed_awards(self):
        """
        Find number of won cursed awards (for all award types).

        :return: [{'type': 'air', 'name': '..', 'img': images/..', 'count': 12}, ...]
        """
        awards = CursedAwards.objects.filter(player__account=self)
        co = Counter()
        for award in awards:
            co.update(award.as_dict(True).keys())
        return [
            {
                'type': c[0],
                'name': CursedAwards.field_to_name[c[0]],
                'img': os.path.join('img/cursed_awards', CursedAwards.field_to_image[c[0]]),
                'count': c[1]
            } for c in co.most_common()
        ]

    class Meta:
        ordering = ['accountid']


class Player(models.Model):
    account = models.ForeignKey(PlayerAccount, blank=True, null=True, on_delete=CASCADE)
    name = models.CharField(max_length=128, db_index=True)
    rank = models.SmallIntegerField()
    skill = models.CharField(max_length=16, blank=True)
    skilluncertainty = models.SmallIntegerField(default=-1, blank=True)
    spectator = models.BooleanField(default=False)
    team = models.ForeignKey("Team", blank=True, null=True, on_delete=CASCADE)
    replay = models.ForeignKey(Replay, on_delete=CASCADE)
    startposx = models.FloatField(blank=True, null=True)
    startposy = models.FloatField(blank=True, null=True)
    startposz = models.FloatField(blank=True, null=True)

    def __unicode__(self):
        return "Player({}, {})".format(self.id, self.name)

    def get_absolute_url(self):
        return reverse('srs/player', args=[self.account.accountid])

    class Meta:
        ordering = ['name']


class Team(models.Model):
    allyteam = models.ForeignKey(Allyteam, on_delete=CASCADE)
    handicap = models.IntegerField()
    rgbcolor = models.CharField(max_length=23)
    side = models.CharField(max_length=32)
    startposx = models.IntegerField(blank=True, null=True)
    startposy = models.IntegerField(blank=True, null=True)
    startposz = models.IntegerField(blank=True, null=True)
    teamleader = models.ForeignKey(Player, related_name="+", on_delete=CASCADE)
    replay = models.ForeignKey(Replay, on_delete=CASCADE)
    num = models.SmallIntegerField()

    def __unicode__(self):
        return "Team({}, {})".format(self.pk, self.teamleader.name)


class MapModOption(models.Model):
    name = models.CharField(max_length=128)
    value = models.CharField(max_length=512)
    replay = models.ForeignKey(Replay, on_delete=CASCADE)

    def __repr__(self):
        return "{}({}, {})".format(self.__class__.__name__, self.pk, self.name)

    def __unicode__(self):
        return self.name


# class Meta:
#         abstract = True

class MapOption(MapModOption):
    pass


class ModOption(MapModOption):
    pass


class NewsItem(models.Model):
    text = models.CharField(max_length=1024)
    post_date = models.DateTimeField(auto_now=True, db_index=True)
    show = models.BooleanField(default=True, db_index=True)

    def __unicode__(self):
        return "NewsItem({}): {}".format(self.pk, self.text[:50])


class UploadTmp(models.Model):
    replay = models.ForeignKey(Replay, on_delete=CASCADE)

    def __unicode__(self):
        return "UploadTmp({}, {})".format(self.pk, self.replay)


# not the most beautiful model, but efficient
class SiteStats(models.Model):
    last_modified = models.DateTimeField(auto_now=True)
    replays = models.IntegerField()
    tags = models.CharField(max_length=1000)
    maps = models.CharField(max_length=1000)
    active_players = models.CharField(max_length=1000)
    all_players = JSONTextField()
    comments = models.CharField(max_length=1000)
    games = models.CharField(max_length=1000)
    bawards = JSONTextField()

    @property
    def bawards_decoded(self):
        return dict(
            (award, ((PlayerAccount.objects.get(pk=ps[0]), ps[1]) for ps in player_stats))
            for award, player_stats in self.bawards.items()
        )


class Game(models.Model):
    name = models.CharField(max_length=256, db_index=True)
    abbreviation = models.CharField(max_length=64, db_index=True)
    sldb_name = models.CharField(max_length=64, db_index=True)
    developer = models.ManyToManyField(User, blank=True)

    def __unicode__(self):
        return "Game({}, {}, {})".format(self.pk, self.abbreviation, self.name[:70])

    def get_absolute_url(self):
        return reverse('srs/browse_archive', args=['game={}'.format(self.pk)])

    class Meta:
        ordering = ['name']


class GameRelease(models.Model):
    name = models.CharField(max_length=256, db_index=True)
    version = models.CharField(max_length=64)
    game = models.ForeignKey(Game, on_delete=CASCADE)

    def __unicode__(self):
        return "GameRelease({}, {}, {}, {})".format(self.pk, self.name[:70], self.version, self.game)

    def get_absolute_url(self):
        return reverse('srs/gamerelease', args=[self.name])

    @property
    def replay_count(self):
        return Replay.objects.filter(gametype=self.name).count()

    class Meta:
        ordering = ['name', 'version']


class RatingBase(models.Model):
    game = models.ForeignKey(Game, on_delete=CASCADE)
    MATCH_TYPE_CHOICES = (('1', u'1v1'),
                          ('T', u'Team'),
                          ('F', u'FFA'),
                          ('G', u'TeamFFA'),
                          ('L', u'Global'),
                          )
    match_type = models.CharField(max_length=1, choices=MATCH_TYPE_CHOICES, db_index=True)
    playeraccount = models.ForeignKey(PlayerAccount, on_delete=CASCADE)
    playername = models.CharField(max_length=128, blank=True, null=True,
                                  db_index=True)  # this fields is redundant, but neccessary for db-side ordering of tables

    trueskill_mu = models.FloatField(default=25.0)
    trueskill_sigma = models.FloatField(default=25.0 / 3)

    @property
    def skilluncertainty(self):
        # from spads_0.11.9.pl - sendPlayerSkill()
        if self.trueskill_sigma > 3:
            return 3
        elif self.trueskill_sigma > 2:
            return 2
        elif self.trueskill_sigma > 1.5:
            return 1
        else:
            return 0

    def __unicode__(self):
        return "{}({}, {}, {}) TS: ({}, {})".format(self.__class__.__name__, self.pk, self.playername,
                                                    self.game.abbreviation, self.match_type,
                                                    self.trueskill_mu, self.trueskill_sigma)

    class Meta:
        ordering = ['-trueskill_mu']
        abstract = True


class Rating(RatingBase):
    pass


class RatingHistory(RatingBase):
    match = models.ForeignKey(Replay, on_delete=CASCADE)
    match_date = models.DateTimeField(blank=True, null=True,
                                      db_index=True)  # this fields is redundant, but neccessary for db-side ordering of tables

    def __unicode__(self):
        return "RatingHistory({}, {}): {}".format(self.pk, self.match_date, super(RatingHistory, self))

    class Meta:
        ordering = ['-match_date', 'playername']


class AdditionalReplayOwner(models.Model):
    uploader = models.ForeignKey(User, on_delete=CASCADE)
    additional_owner = models.ForeignKey(PlayerAccount, on_delete=CASCADE)

    def __unicode__(self):
        return u"AdditionalReplayOwner({}) uploader: {}, additional_owner: {}".format(self.id, self.uploader,
                                                                                      self.additional_owner)

    class Meta:
        ordering = ['uploader__username']


class ExtraReplayMedia(models.Model):
    replay = models.ForeignKey(Replay, on_delete=CASCADE)
    uploader = models.ForeignKey(User, on_delete=CASCADE)
    upload_date = models.DateTimeField(auto_now_add=True, db_index=True)
    comment = models.CharField(max_length=513)
    media = models.FileField(upload_to="media/%Y/%m/%d", blank=True)
    image = models.ImageField(upload_to="image/%Y/%m/%d", blank=True)
    media_magic_text = models.CharField(max_length=1024, blank=True, null=True)
    media_magic_mime = models.CharField(max_length=128, blank=True, null=True)

    @property
    def media_basename(self):
        return basename(self.media.name)

    @property
    def image_basename(self):
        return basename(self.image.name)

    def __unicode__(self):
        return u"ExtraReplayMedia({}) replay: {} media: {} image: {} by: {} on: {}".format(
            self.pk, self.replay, self.media, self.image, self.uploader, self.upload_date)

    class Meta:
        ordering = ['-upload_date']


class SldbLeaderboardGame(models.Model):
    last_modified = models.DateTimeField(auto_now_add=True)
    game = models.ForeignKey(Game, on_delete=CASCADE)
    match_type = models.CharField(max_length=1, choices=RatingBase.MATCH_TYPE_CHOICES, db_index=True)

    def __unicode__(self):
        return u"SldbLeaderboardGame({}, {}, {})".format(self.pk, self.game, self.match_type)


class SldbLeaderboardPlayer(models.Model):
    leaderboard = models.ForeignKey(SldbLeaderboardGame, on_delete=CASCADE)
    account = models.ForeignKey(PlayerAccount, on_delete=CASCADE)
    rank = models.IntegerField()
    trusted_skill = models.FloatField()
    estimated_skill = models.FloatField()
    uncertainty = models.FloatField()
    inactivity = models.IntegerField()

    def __unicode__(self):
        return u"SldbLeaderboardPlayer({}, {}, {}, {}, {})".format(self.pk, self.leaderboard, self.rank, self.account,
                                                                  self.trusted_skill)

    class Meta:
        ordering = ['rank']


class SldbMatchSkillsCache(models.Model):
    last_modified = models.DateTimeField(auto_now_add=True)
    gameID = models.CharField(max_length=32, unique=True)
    text = models.TextField()

    def __unicode__(self):
        return u"SldbMatchSkillsCache({}, {}, {})".format(self.pk, self.gameID, self.text)

    @staticmethod
    def purge_old():
        """
        Remove >= 30 minutes old entries
        """
        SldbMatchSkillsCache.objects.filter(
            last_modified__lt=datetime.datetime.now(tz=Replay.objects.latest().unixTime.tzinfo) - datetime.timedelta(
                minutes=30)).delete()


class SldbPlayerTSGraphCache(models.Model):
    last_modified = models.DateTimeField(auto_now_add=True)
    account = models.ForeignKey(PlayerAccount, on_delete=CASCADE)
    game = models.ForeignKey(Game, on_delete=CASCADE)
    filepath_global = models.CharField(max_length=256)
    filepath_duel = models.CharField(max_length=256)
    filepath_ffa = models.CharField(max_length=256)
    filepath_team = models.CharField(max_length=256)
    filepath_teamffa = models.CharField(max_length=256)

    match_type2sldb_name = {"1": "Duel", "T": "Team", "F": "FFA", "G": "Global", "L": "TeamFFA"}

    def __unicode__(self):
        return u"SldbPlayerTSGraphCache({}) {} | {} | {}".format(self.pk, self.account, self.game, self.filepath_global)

    def remove_files(self):
        for filepath in (self.filepath_global, self.filepath_duel, self.filepath_ffa, self.filepath_team, self.filepath_teamffa):
            if "static/img/" in filepath:
                # don't remove static error / info images
                continue
            else:
                try:
                    os.remove(filepath)
                except OSError as exc:
                    logger.warning("Cannot remove file '%s' of cache entry %d: %s", filepath, self.id, exc)

    @staticmethod
    def purge_old():
        """
        Remove >= 30 days old entries
        """
        old_entries = SldbPlayerTSGraphCache.objects.filter(last_modified__lt=datetime.datetime.now(
            tz=Replay.objects.latest().unixTime.tzinfo) - datetime.timedelta(days=30))
        if old_entries.exists():
            logger.debug("Deleting stale SldbPlayerTSGraphCache objects: %s", old_entries)
            for entry in old_entries:
                entry.remove_files()
            old_entries.delete()

    def as_dict(self):
        return {
            "Global": self.filepath_global,
            "Duel": self.filepath_duel,
            "FFA": self.filepath_ffa,
            "Team": self.filepath_team,
            "TeamFFA": self.filepath_teamffa
        }


class BAwards(models.Model):
    replay = models.ForeignKey(Replay, on_delete=CASCADE)
    ecoKillAward1st = models.ForeignKey(Player, blank=True, null=True, related_name="+", on_delete=CASCADE)
    ecoKillAward1stScore = models.IntegerField(default=-1)
    ecoKillAward2nd = models.ForeignKey(Player, blank=True, null=True, related_name="+", on_delete=CASCADE)
    ecoKillAward2ndScore = models.IntegerField(default=-1)
    ecoKillAward3rd = models.ForeignKey(Player, blank=True, null=True, related_name="+", on_delete=CASCADE)
    ecoKillAward3rdScore = models.IntegerField(default=-1)
    fightKillAward1st = models.ForeignKey(Player, blank=True, null=True, related_name="+", on_delete=CASCADE)
    fightKillAward1stScore = models.IntegerField(default=-1)
    fightKillAward2nd = models.ForeignKey(Player, blank=True, null=True, related_name="+", on_delete=CASCADE)
    fightKillAward2ndScore = models.IntegerField(default=-1)
    fightKillAward3rd = models.ForeignKey(Player, blank=True, null=True, related_name="+", on_delete=CASCADE)
    fightKillAward3rdScore = models.IntegerField(default=-1)
    effKillAward1st = models.ForeignKey(Player, blank=True, null=True, related_name="+", on_delete=CASCADE)
    effKillAward1stScore = models.FloatField(default=-1)
    effKillAward2nd = models.ForeignKey(Player, blank=True, null=True, related_name="+", on_delete=CASCADE)
    effKillAward2ndScore = models.FloatField(default=-1)
    effKillAward3rd = models.ForeignKey(Player, blank=True, null=True, related_name="+", on_delete=CASCADE)
    effKillAward3rdScore = models.FloatField(default=-1)
    cowAward = models.ForeignKey(Player, blank=True, null=True, related_name="+", on_delete=CASCADE)
    cowAwardScore = models.IntegerField(default=-1)
    ecoAward = models.ForeignKey(Player, blank=True, null=True, related_name="+", on_delete=CASCADE)
    ecoAwardScore = models.IntegerField(default=-1)
    dmgRecAward = models.ForeignKey(Player, blank=True, null=True, related_name="+", on_delete=CASCADE)
    dmgRecAwardScore = models.FloatField(default=-1)
    sleepAward = models.ForeignKey(Player, blank=True, null=True, related_name="+", on_delete=CASCADE)
    sleepAwardScore = models.IntegerField(default=-1)

    def __unicode__(self):
        return u"BAwards({}) Replay: {} | EcoKill: {},{},{} | FightKill: {},{},{} | EffKill: {},{},{} | Cow: {} | " \
               u"Eco: {} | DmgRec: {} | Sleep: {}".format(
            self.pk, self.replay.pk, self.ecoKillAward1st, self.ecoKillAward2nd, self.ecoKillAward3rd,
            self.fightKillAward1st, self.fightKillAward2nd, self.fightKillAward3rd, self.effKillAward1st,
            self.effKillAward2nd, self.effKillAward3rd, self.cowAward, self.ecoAward, self.dmgRecAward, self.sleepAward)


class XTAwards(models.Model):
    replay = models.ForeignKey(Replay, on_delete=CASCADE)
    isAlive = models.SmallIntegerField(default=-1)
    player = models.ForeignKey(Player, on_delete=CASCADE)
    unit = models.CharField(max_length=1024)
    kills = models.IntegerField(default=-1)
    age = models.IntegerField(default=-1)

    def __unicode__(self):
        return u"XTAwards({}) Replay: {} | isAlive: {} | player: {} | unit: {} | kills: {} | age: {}".format(
            self.pk, self.replay.pk, self.isAlive, self.player.name, self.unit, self.kills, self.age)


class CursedAwards(models.Model):
    replay = models.ForeignKey(Replay, on_delete=CASCADE)
    player = models.ForeignKey(Player, on_delete=CASCADE)

    air = models.PositiveIntegerField(default=0)
    bug = models.PositiveIntegerField(default=0)
    cap = models.PositiveIntegerField(default=0)
    dran = models.PositiveIntegerField(default=0)
    drankill = models.PositiveIntegerField(default=0)
    emp = models.PositiveIntegerField(default=0)
    fire = models.PositiveIntegerField(default=0)
    friend = models.PositiveIntegerField(default=0)
    heart = models.PositiveIntegerField(default=0)
    hero = models.PositiveIntegerField(default=0)
    herokill = models.PositiveIntegerField(default=0)
    hover = models.PositiveIntegerField(default=0)
    kam = models.PositiveIntegerField(default=0)
    lycan = models.PositiveIntegerField(default=0)
    mex = models.PositiveIntegerField(default=0)
    mexkill = models.PositiveIntegerField(default=0)
    nux = models.PositiveIntegerField(default=0)
    ouch = models.PositiveIntegerField(default=0)
    point = models.PositiveIntegerField(default=0)
    pwn = models.PositiveIntegerField(default=0)
    rezz = models.PositiveIntegerField(default=0)
    share = models.PositiveIntegerField(default=0)
    shell = models.PositiveIntegerField(default=0)
    slow = models.PositiveIntegerField(default=0)
    sweeper = models.PositiveIntegerField(default=0)

    field_to_image = dict(
        air='trophy_air.png',
        bug='trophy_bug.png',
        cap='trophy_cap.png',
        dran='trophy_dran.png',
        drankill='trophy_dragon.png',
        emp='trophy_emp.png',
        fire='trophy_fire.png',
        friend='trophy_friend.png',
        heart='trophy_heart.png',
        hero='trophy_hero.png',
        herokill='trophy_herokill.png',
        hover='trophy_hover.png',
        kam='trophy_kam.png',
        lycan='trophy_lycan.png',
        mex='trophy_mex.png',
        mexkill='trophy_mexkill.png',
        nux='trophy_nux.png',
        ouch='trophy_ouch.png',
        point='trophy_point.png',
        pwn='trophy_pwn.png',
        rezz='trophy_rezz.png',
        share='trophy_share.png',
        shell='trophy_shell.png',
        slow='trophy_slow.png',
        sweeper='trophy_sweeper.png',
    )

    field_to_name = dict(
        air='Airforce General',
        bug='Bug Hunter',
        cap='Mind Magician',
        dran='Dragons & Angels',
        drankill='Dragon & Angel Slayer',
        emp='Stun Wizard',
        fire='Master Grill-Chef',
        friend='Friendly Fire Award',
        heart='Queen Heart Breaker',
        hero='Heros do the job',
        herokill='Hero Hunter',
        hover='Hover Admiral',
        kam='Kamikaze Award',
        lycan='Werewolf Hunter',
        mex='Mineral Prospector',
        mexkill='Loot & Pillage',
        nux='Apocalyptic Achievement Award',
        ouch='Big Purple Heart',
        point='This is my Land',
        pwn='Total Pain',
        rezz='Vile Necromancer',
        share='Share Bear',
        shell='Turtle Shell',
        slow='Traffic Cop',
        sweeper='Land Sweeper',
    )

    @classmethod
    def sorted_field_names(cls):
        return sorted([f.name for f in cls._meta.fields if f.name not in ('id', 'replay', 'player')])

    def as_dict(self, only_positive=False):
        res = dict()
        for field_name in self.sorted_field_names():
            val = getattr(self, field_name)
            if only_positive and not val > 0:
                continue
            res[field_name] = val
        return res

    def __unicode__(self):
        return u"CursedAwards({}, {}, {})".format(
            self.pk,
            self.replay.pk,
            [(f.name, f.value_from_object(self)) for f in self._meta.fields if f.name not in ('id', 'replay', 'player') and f.value_from_object(self) > 0]
        )


def get_owner_list(uploader):
    res = [uploader]
    res.extend(AdditionalReplayOwner.objects.filter(uploader=uploader))
    return res


@background
def update_stats(force=False):
    """
    some very expensive operations -> this runs only once per day
    :arg force: bool: run even if has already run in the last 24h
    """
    # statistics like most played maps, most used tags etc. (sed in the browse and all_players views)
    sist, created = SiteStats.objects.get_or_create(id=1, defaults={'replays': 0, 'tags': "", 'maps': "",
                                                                    "active_players": "", 'all_players': "",
                                                                    'comments': "", "games": "", "bawards": ""})
    if created or force or (datetime.datetime.now(tz=sist.last_modified.tzinfo) - sist.last_modified).days > 0:
        # update stats
        logger.info("starting stats update...")
        timer = SrsTiming()
        timer.start("update_stats()")
        replays = Replay.objects.count()
        now = datetime.datetime.now(timezone.get_current_timezone())
        start_date = now - datetime.timedelta(days=30)
        if settings.DEBUG:
            # no daily uploads on my dev pc - list can be empty
            start_date = now - datetime.timedelta(days=300)
        default_tags = Tag.objects.filter(
            name__in=["1v1", "2v2", "3v3", "4v4", "5v5", "6v6", "7v7", "8v8", "Team", "FFA", "TeamFFA", "Tourney"])
        tags = default_tags.annotate(num_replay=Count('replay'))
        maps = Map.objects.filter(replay__unixTime__range=(start_date, now)).annotate(
            num_replay=Count('replay')).order_by('-num_replay')[:10]

        # statistic on number of matches of each game (for browse page)
        timer.start("games")
        games = list()
        for game in Game.objects.all():
            games.append((
                game.id,
                Replay.objects.filter(gametype__in=game.gamerelease_set.values_list("name", flat=True)).count()))
        games.sort(key=operator.itemgetter(1), reverse=True)
        timer.stop("games")

        # most active players in the last 30 days (for browse page)
        timer.start("active_players")
        active_players = PlayerAccount.objects.filter(accountid__gt=0,
                                                      player__spectator=False,
                                                      player__replay__unixTime__range=(start_date, now)
                                                      ).annotate(Count("player__replay")
                                                                 ).order_by("-player__replay__count", "accountid")
        timer.stop("active_players")

        # newest comments (for index page)
        comments = Comment.objects.filter(is_removed=False).reverse()[:5]

        # encode stats into strings
        timer.start("strings")
        if tags.exists():
            tags_s = "|".join(["{}.{}".format(t.id, t.num_replay) for t in tags])
        else:
            tags_s = ""
        if maps.exists():
            # map.id . #matches_last_30d / #matches_total
            maps_s = "|".join(["{}.{} / {}".format(m.id, m.num_replay, Replay.objects.filter(map_info=m).count())
                               for m in maps])
        else:
            maps_s = ""
        if active_players:
            act_pls_s = "|".join(["{}.{}".format(pa.id, pa.player__replay__count) for pa in active_players[:20]])
        else:
            act_pls_s = ""
        if comments.exists():
            comments_s = "|".join(map(str, comments.values_list("id", flat=True)))
        else:
            comments_s = ""
        if games:
            games_s = "|".join(["{}.{}".format(*g) for g in games])
        else:
            games_s = ""
        timer.stop("strings")

        #  player names and urls (for all_players page)
        timer.start("all_players")

        pl_pas = PlayerAccount.objects.filter(accountid__gt=0, player__isnull=False).values(
            "accountid", "player__name").order_by("player__name").distinct()
        all_players = [("/player/{}/".format(pl["accountid"]), pl["player__name"]) for pl in pl_pas]
        timer.stop("all_players")

        # BAwards statistics (for hall of fame)
        timer.start("bawards")
        bawards_fields = [field.name for field in BAwards._meta.get_fields()
                          if "Award" in field.name and "Score" not in field.name]
        bawards_stats = dict([(field, defaultdict(int)) for field in bawards_fields])
        bawards_no_bots = BAwards.objects.exclude(replay__player__account__accountid=0)
        for field in bawards_fields:
            arg = {"{}__isnull".format(field): False}
            for pa_pk in PlayerAccount.objects.filter(
                    player__in=bawards_no_bots.filter(**arg).values(field)
            ).values_list("pk", flat=True):
                bawards_stats[field][pa_pk] += 1
            # converting dict to list, sort, keep only top 10
            bawards_stats[field] = sorted(bawards_stats[field].items(), key=operator.itemgetter(1), reverse=True)[:10]
        timer.stop("bawards")

        timer.start("save()")
        sist.replays = replays
        sist.tags = tags_s
        sist.maps = maps_s
        sist.active_players = act_pls_s
        sist.all_players = all_players
        sist.comments = comments_s
        sist.games = games_s
        sist.bawards = bawards_stats
        sist.save()
        timer.stop("save()")
        timer.stop("update_stats()")
        logger.info("timings:\n%s", timer)
        return sist


# TODO: use a proxy model for this
User.get_absolute_url = lambda self: "/player/{}/".format(self.userprofile.accountid)
User.replays_uploaded = lambda self: Replay.objects.filter(uploader=self).count()

# TODO: use a proxy model for this
Comment.replay = lambda self: self.content_object.__unicode__()
Comment.comment_short = lambda self: "{}...".format(self.comment[:50])


class SrsTiming(object):
    def __init__(self):
        self.times = dict()
        self.counter = 0

    def start(self, name):
        self.times[name] = (self.counter, datetime.datetime.now(), name)
        self.counter += 1

    def stop(self, name):
        self.times[name] = (self.times[name][0], datetime.datetime.now() - self.times[name][1], name)

    @property
    def sorted_list(self):
        return sorted(self.times.values(), key=operator.itemgetter(0))

    def __str__(self):
        return "\n".join([
            f"{t[2]}: {t[1].seconds}.{int(t[1].microseconds / 10000)}"
            for t in self.sorted_list
        ])


# HEAVY DEBUG
# automatically log each DB object save
# @receiver(post_save)
# def obj_save_callback(sender, instance, **kwargs):
#    # Session obj has u'str encoded hex key as pk
#    logger.debug("%s.save(%s) : '%s'", instance.__class__.__name__, instance.pk, instance)

# automatically log each DB object delete
# @receiver(post_delete)
# def obj_del_callback(sender, instance, **kwargs):
#    # Session obj has u'str encoded hex key as pk
#    logger.debug("%s.delete(%s) : '%s'", instance.__class__.__name__, instance.pk, instance)

# automatically refresh statistics when a replay is created or modified
@receiver(post_save, sender=Replay)
def replay_save_callback(sender, instance, **kwargs):
    logger.debug("Replay.save(%d) : '%s'", instance.pk, instance)
    # check for new new Game[Release] object
    if kwargs.get("created"):
        Notifications().new_replay(instance)
        update_stats()


# automatically refresh statistics when a replay is deleted
@receiver(post_delete, sender=Replay)
def replay_del_callback(sender, instance, **kwargs):
    update_stats()


# automatically refresh statistics when a comment is created or modified
@receiver(post_save, sender=Comment)
def comment_save_callback(sender, instance, **kwargs):
    if instance.content_type == ContentType.objects.get(model="infolog"):
        Notifications().new_comment(instance)
    update_stats()


# automatically refresh statistics when a comment is deleted
@receiver(post_delete, sender=Comment)
def comment_del_callback(sender, instance, **kwargs):
    update_stats()


# automatically log creation of PlayerAccounts
@receiver(post_save, sender=PlayerAccount)
def playerAccount_save_callback(sender, instance, **kwargs):
    logger.debug("PlayerAccount.save(%d): accountid=%d preffered_name=%s", instance.pk, instance.accountid,
                 instance.preffered_name)
