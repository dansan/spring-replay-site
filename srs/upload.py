# This file is part of the "spring relay site / srs" program. It is published
# under the GPLv3.
#
# Copyright (C) 2016-2020 Daniel Troeder (daniel #at# admin-box #dot# com)
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import logging
import shutil
import stat
from tempfile import mkstemp
import gzip
import pprint
import magic
import datetime
import os
import errno
from os.path import join as path_join

from django.db.models import Min
from django.contrib.sitemaps import ping_google
import django.contrib.auth
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
import django.utils.timezone

import coreapi

from srs.models import (AdditionalReplayInfo, Allyteam, BAwards, Map, MapImg, MapOption, ModOption, Player,
                        PlayerAccount, PlayerStats, RatingHistory, Replay, Tag, Team, TeamStats, UploadTmp, XTAwards,
                        SrsTiming, CursedAwards)
import srs.parse_demo_file as parse_demo_file
import srs.springmaps as springmaps
from srs.sldb import demoskill2float, get_sldb_match_skills, sldb_gametype2matchtype, SLDBError

logger = logging.getLogger(__name__)
timer = None


class UploadError(Exception):
    def __init__(self, demofile, *args, **kwargs):
        self.demofile = demofile
        super(UploadError, self).__init__(*args, **kwargs)


class AlreadyExistsError(UploadError):
    def __init__(self, demofile, replay, *args, **kwargs):
        self.replay = replay
        super(AlreadyExistsError, self).__init__(demofile, *args, **kwargs)


def xmlrpc_upload(username, password, filename, demofile, subject, comment, tags, owner):
    global timer
    logger.info("username='%s' password=xxxxxx filename='%s' subject='%s' comment='%s' tags='%s' owner='%s'", username,
                filename, subject, comment, tags, owner)

    # authenticate uploader
    user = django.contrib.auth.authenticate(username=username, password=password)
    if user is not None and user.is_active:
        logger.info("Authenticated user '%s'", user)
    else:
        logger.info("Uploader wrong password, account unknown or inactive, abort.")
        return "1 Unknown or inactive uploader account or bad password."

    # find owner account
    try:
        owner_ac = User.objects.get(username__iexact=owner)
        logger.info("Owner is '%s'", owner_ac)
    except ObjectDoesNotExist:
        logger.info("Owner '%s' unknown on replays site, abort.", owner)
        return "2 Unknown or inactive owner account, please log in via web interface once."

    timer = SrsTiming()
    timer.start("xmlrpc_upload()")
    (path, written_bytes) = save_uploaded_file(demofile.data, filename)

    logger.info("User '%s' uploaded file '%s' with title '%s', parsing it now.", username, path, subject)
    try:
        replay, msg = parse_uploaded_file(path, timer, tags, subject, comment, owner_ac)
    except UploadError as exc:
        return str(exc)
    return msg


def parse_uploaded_file(path, timer, tags, subject, comment, owner_ac, move=True, reparse_if_exists=True):
    # renice to 10
    current_niceness = os.nice(0)
    os.nice(max(0, 10 - current_niceness))

    timer.start("parse_uploaded_file()")
    timer.start("parse_demo_file.Parse_demo_file()")
    demofile = parse_demo_file.Parse_demo_file(path)
    timer.stop("parse_demo_file.Parse_demo_file()")
    demofile.check_magic()
    timer.start("parse()")
    demofile.parse()
    timer.stop("parse()")

    try:
        replay = Replay.objects.get(gameID=demofile.header["gameID"])
        if replay.was_succ_uploaded:
            logger.warning("Replay already existed: pk=%d gameID=%s", replay.pk, replay.gameID)
            if reparse_if_exists:
                logger.warning("########### Reparsing... ###########")
                res = reparse(replay, path, tags, subject, comment, owner_ac)
                timer.stop("parse_uploaded_file()")
                return res
            if move:
                try:
                    os.remove(path)
                except OSError as exc:
                    logger.warning("Could not remove file '%s': %s", path, exc)
            raise AlreadyExistsError(demofile, replay, '3 uploaded replay already exists as "{}" at "{}"'.format(
                replay.__unicode__(), replay.get_absolute_url()))
        else:
            logger.info("Deleting existing unsuccessfully uploaded replay '%s' (%d, %s)", replay, replay.pk,
                        replay.gameID)
            del_replay(replay)
            UploadTmp.objects.filter(replay=replay).delete()
    except ObjectDoesNotExist:
        # is new replay
        pass

    new_filename = os.path.basename(path).replace(" ", "_")
    year = str(datetime.date.today().year)
    month = str(datetime.date.today().month)
    target_dir = os.path.join(settings.REPLAYS_PATH, year, month)
    try:
        os.makedirs(target_dir, 0o755)
    except OSError as exc:
        if getattr(exc, 'errno', 0) != errno.EEXIST:
            logger.exception('Creating directory %r.', target_dir)
            raise
    newpath = os.path.join(target_dir, new_filename)
    if move:
        shutil.move(path, newpath)
        logger.info('Moved %r to %r.', path, newpath)
    else:
        shutil.copy2(path, newpath)
        logger.info('Copied %r to %r.', path, newpath)
    os.chmod(newpath, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH)
    try:
        timer.start("store_demofile_data()")
        replay = store_demofile_data(demofile, tags, newpath, subject, comment, owner_ac)
    except:
        logger.error("FIXME: to broad exception handling.")
        logger.exception("Error in store_demofile_data()")
        raise
    finally:
        timer.stop("store_demofile_data()")

    if 'ba_platform_stats' in demofile.additional:
        try:
            timer.start("upload_platform_stats()")
            upload_platform_stats(demofile)
        except Exception as exc:
            logger.error("Error uploading platform stats for replay(%d | %s): %s", replay.id, replay, exc)
        finally:
            timer.stop("upload_platform_stats()")

    demofile = None

    logger.info("New replay created: pk=%d gameID=%s", replay.pk, replay.gameID)
    try:
        timer.start("rate_match()")
        rate_match(replay)
    except Exception as exc:
        logger.error("Error rating replay(%d | %s): %s", replay.id, replay, exc)
    finally:
        timer.stop("rate_match()")

    if not settings.DEBUG:
        try:
            timer.start("ping_google()")
            ping_google("/sitemap.xml")
        except Exception as exc:
            logger.error("FIXME: to broad exception handling.")
            logger.exception("ping_google(): %s", exc)
            pass
        finally:
            timer.stop("ping_google()")

    timer.stop("parse_uploaded_file()")

    return replay, '0 replay at "{}"'.format(replay.get_absolute_url())


def save_uploaded_file(ufile, filename):
    """
    may raise an exception from os.open/write/close()
    """
    suff = filename.split("_")[-1]
    filemagic = magic.from_buffer(ufile, mime=True)
    if isinstance(ufile, bytes):
        open_mode = "wb"
    else:
        open_mode = "w"
    if filemagic.endswith("gzip"):
        (fd, path) = mkstemp(suffix="_{}".format(suff), prefix="{}__".format(filename[:-len(suff) - 1]))
        f = os.fdopen(fd, open_mode)
    else:
        (fd, path) = mkstemp(suffix="_{}.gz".format(suff), prefix="{}__".format(filename[:-len(suff) - 1]))
        f = gzip.GzipFile(filename=None, mode="w", compresslevel=6, fileobj=os.fdopen(fd, open_mode))
    written_bytes = f.write(ufile)
    f.close()
    logger.debug("stored file with %r bytes in %r", written_bytes, path)
    return path, len(ufile)


def store_demofile_data(demofile, tags, path, short, long_text, user):
    """
    Store all data about this replay in the database,
    if replay exists, all argument except 'demofile' are ignored
    """
    global timer
    logger.info('gameID=%r tags=%r path=%r short=%r long_text=%r user=%r', demofile.header['gameID'], tags, path, short, long_text, user)
    if not timer:
        timer = SrsTiming()
    #     pp = pprint.PrettyPrinter(depth=6)
    #     logger.debug("demofile.__dict__: %s",pp.pformat(demofile.__dict__))
    try:
        replay = Replay.objects.get(gameID=demofile.header["gameID"])
        replay.download_count = 0
        logger.debug("reparsing existing %s", replay)
    except ObjectDoesNotExist:
        replay = Replay()
        logger.debug("new Replay: gameID: %s", demofile.header["gameID"])

    replay.published = False
    if user is not None:
        replay.uploader = user
    if short is not None:
        replay.title = short  # temp

    # copy match infos
    for key in ["versionString", "gameID", "wallclockTime"]:
        replay.__setattr__(key, demofile.header[key])
    replay.unixTime = datetime.datetime.strptime(demofile.header["unixTime"], "%Y-%m-%d %H:%M:%S").replace(
        tzinfo=django.utils.timezone.get_current_timezone())
    for key in ["autohostname", "gametype", "startpostype"]:
        if key in demofile.game_setup["host"]:
            replay.__setattr__(key, demofile.game_setup["host"][key])

    # if match is <2 min long, don't rate it
    replay.notcomplete = demofile.header['gameTime'].startswith("0:00:") or demofile.header['gameTime'].startswith(
        "0:01:")
    logger.info("gameTime=%r -> replay.notcomplete=%r", demofile.header['gameTime'], replay.notcomplete)

    if path is not None:
        replay.filename = os.path.basename(path)
        replay.path = os.path.dirname(path)
        replay.save()
        UploadTmp.objects.create(replay=replay)

        logger.debug("replay(%d) gameID='%s' unixTime='%s' created", replay.pk, replay.gameID, replay.unixTime)

    # save AllyTeams
    timer.start("  allyteams")
    allyteams = {}
    at_depr = Allyteam.objects.filter(replay=replay, num=-1)
    if at_depr.exists():
        logger.info("removing deprecated Allyteams: %s", at_depr.values_list('id'))
        at_depr.delete()
    for anum, val in demofile.game_setup['allyteam'].items():
        defaults = {"numallies": val["numallies"], "winner": int(anum) in demofile.winningAllyTeams,
                    "startrectbottom": val.get("startrectbottom"), "startrectleft": val.get("startrectleft"),
                    "startrectright": val.get("startrectright"), "startrecttop": val.get("startrecttop")}
        allyteam, created = Allyteam.objects.get_or_create(replay=replay, num=anum, defaults=defaults)
        if not created:
            for k, v in defaults.items():
                setattr(allyteam, k, v)
            allyteam.save()
        allyteams[anum] = allyteam

    timer.stop("  allyteams")
    logger.debug("replay(%d) allyteams: %s", replay.pk, [a.pk for a in allyteams.values()])

    # save tags
    save_tags(replay, tags)

    # save map and mod options
    def truncate_option(k, v):
        if len(str(k)) > 512:
            k = "string to long, sorry"
        if len(str(v)) > 512:
            v = "string to long, sorry"
        return k, v

    timer.start("  map+modoptions")
    for k, v in demofile.game_setup['mapoptions'].items():
        k, v = truncate_option(k, v)
        MapOption.objects.get_or_create(name=k, value=v, replay=replay)

    for k, v in demofile.game_setup['modoptions'].items():
        k, v = truncate_option(k, v)
        ModOption.objects.get_or_create(name=k, value=v, replay=replay)
    timer.stop("  map+modoptions")

    logger.debug("replay(%d) added mapoptions, modoptions and tags: %s", replay.pk,
                 replay.tags.all().values_list("name"))

    # save players and their accounts
    timer.start("  players and playeraccounts")
    # add late-connected spectators
    # TODO: add /joinas players
    for late_spec_name, late_spec_val in demofile.spectators.items():
        if (hasattr(late_spec_val, "connected") and
                late_spec_val.connected and
                hasattr(late_spec_val, "playerNum") and
                    late_spec_val.playerNum not in demofile.game_setup['player'].keys()):
            # found a spec that connected, but was not in the start script
            # -> late-connected
            # To add it, the problem is that we don't have the required
            # data for a proper Player object (we have only the name). We
            # try to find the correct Player[Account] by looking at existing
            # Players from previous Replays:
            players_w_late_spec_name = Player.objects.filter(name=late_spec_name, replay__id__lt=replay.id).order_by(
                "-id")
            if players_w_late_spec_name.exists():
                player_w_late_spec_name = players_w_late_spec_name[0]
                accid = player_w_late_spec_name.account.accountid
                cc = player_w_late_spec_name.account.countrycode
                rank = player_w_late_spec_name.rank
                skill = player_w_late_spec_name.skill
                skilluncertainty = player_w_late_spec_name.skilluncertainty
            else:
                accid = None
                cc = "??"
                rank = 0
                skill = ""
                skilluncertainty = -1

            # add spectator to list of players from script
            demofile.game_setup['player'][late_spec_val.playerNum] = dict(accountid=accid,
                                                                          ally=-1,
                                                                          connected=True,
                                                                          countrycode=cc,
                                                                          name=late_spec_name,
                                                                          num=late_spec_val.playerNum,
                                                                          password='',
                                                                          rank=rank,
                                                                          skill=skill,
                                                                          skilluncertainty=skilluncertainty,
                                                                          spectator=1,
                                                                          startposx=-1)
            logger.debug("added late-spec %s", late_spec_name)

    players = dict()
    teams = list()
    for pnum in sorted(demofile.game_setup['player'].keys()):
        player = demofile.game_setup['player'][pnum]
        set_accountid(player)
        if player["countrycode"] is None:
            player["countrycode"] = "??"
        pa, _ = PlayerAccount.objects.get_or_create(accountid=player["accountid"],
                                                    defaults={'countrycode': player["countrycode"],
                                                              'preffered_name': player["name"]})
        if pa.preffered_name == "??" or pa.preffered_name == "":
            pa.preffered_name = player["name"]
            pa.save()
        if pa.countrycode == "??":
            pa.countrycode = player["countrycode"]
            pa.save()
        try:
            skill = player["skill"]
        except KeyError:
            skill = ""
        try:
            skilluncertainty = player["skilluncertainty"]
        except KeyError:
            skilluncertainty = -1

        if player["rank"] is None:
            try:
                rank = Player.objects.filter(account=pa).order_by("-id")[0].rank
            except KeyError:
                rank = 0
        else:
            rank = player["rank"]
        defaults = {"name": player["name"], "rank": rank, "skill": skill,
                    "skilluncertainty": skilluncertainty, "spectator": bool(player["spectator"])}
        players[pnum], created = Player.objects.get_or_create(replay=replay, account=pa, defaults=defaults)
        if not created:
            for k, v in defaults.items():
                setattr(players[pnum], k, v)

        if pa.accountid > 0 and not (
                            player['spectator'] == 1 and 'startposx' in player and player['startposx'] == -1):
            # if we found players w/o account, and now have a player with the
            # same name, but with an account - unify them
            # exclude freshly created players from late-join
            pac = Player.objects.filter(name=player["name"], account__accountid__lt=0)
            if pac.exists():
                logger.info("replay(%d) found matching name-account info for previously accountless Player(s):",
                            replay.pk)
                logger.info("replay(%d) PA.pk=%d Player(s).pk:%s", replay.pk, pa.pk, [(p.name, p.pk) for p in pac])
                for pplayer in pac:
                    try:
                        pplayer.account.delete()
                    except ObjectDoesNotExist:
                        pass
                    pplayer.account = pa
                    pplayer.save()

        if "team" in player and player["team"] is not None:
            teams.append((players[pnum], player["team"]))  # [(Player, "2"), ...]

            try:
                players[pnum].startposx = player["startposx"]
                players[pnum].startposy = player["startposy"]
                players[pnum].startposz = player["startposz"]
            except KeyError:
                logger.info("player has no start coords. (quit/kicked/not connected?) player: %s players[%d]: %s",
                            player, pnum, players[pnum])
        else:
            # this must be a spectator
            if not player["spectator"] == 1:
                logger.error("replay(%d) found player without team and not a spectator: %s", replay.pk, player)
            try:
                # late-join spec
                players[pnum].startposx = player["startposx"]
            except KeyError:
                pass
        players[pnum].save()
    timer.stop("  players and playeraccounts")

    logger.debug("replay(%d) saved PlayerAccounts and Players: %s", replay.pk, [Player.objects.filter(replay=replay)])

    # save teams
    timer.start("  teams")
    team_depr = Team.objects.filter(replay=replay, num=-1)
    if team_depr.exists():
        logger.info("removing deprecated Teams: %s", team_depr.values_list('id'))
        team_depr.delete()
    for tnum, val in demofile.game_setup['team'].items():
        defaults = {"allyteam": allyteams[val["allyteam"]], "handicap": val["handicap"],
                    "rgbcolor": floats2rgbhex(val.get("rgbcolor", 1.0)), "side": val["side"],
                    "teamleader": players[val["teamleader"]]}
        if "rgbcolor" not in val:
            # probably zero-k, let's see and learn what stuff they use instead
            logger.error("No key 'rgbcolor' in game_setup of team %r, val=%r ", tnum, val)
        try:
            defaults["startposx"] = val["startposx"]
            defaults["startposy"] = val["startposy"]
            defaults["startposz"] = val["startposz"]
        except KeyError:
            pass
        team, created = Team.objects.get_or_create(replay=replay, num=tnum, defaults=defaults)
        if not created:
            for k, v in defaults.items():
                setattr(team, k, v)
            team.save()

        # find Players for this Team
        teamplayers = [t[0] for t in teams if t[1] == tnum]
        if teamplayers:
            for player in teamplayers:
                player.team = team
                player.save()
        else:
            # team without player: this is a bot - create a Player for it
            logger.debug("replay(%d) team[%s] (Team(%d)) has no teamplayers, must be a bot", replay.pk, tnum, team.pk)
            bot_pa = PlayerAccount.objects.get(accountid=0)
            Player.objects.create(account=bot_pa, name="Bot (of {})".format(team.teamleader.name), rank=1, spectator=False,
                                  team=team, replay=replay)

            # add a "Bot" tag
            bottag, _ = Tag.objects.get_or_create(name="Bot")
            replay.tags.add(bottag)

            # detect single player and add tag
            try:
                if demofile.game_setup["host"]["hostip"] == "" and demofile.game_setup["host"]["ishost"] == 1:
                    sptag, _ = Tag.objects.get_or_create(name="Single Player")
                    replay.tags.add(sptag)
            except KeyError:
                pass

    timer.stop("  teams")
    logger.debug("replay(%d) saved Teams (%s)", replay.pk, Team.objects.filter(replay=replay).values_list('id'))

    # work around XTA and Zero-Ks usage of empty AllyTeams
    at_empty = Allyteam.objects.filter(replay=replay, team__isnull=True)
    if at_empty.exists():
        logger.debug("replay(%s) deleting useless AllyTeams: %s", replay.pk, at_empty)
        at_empty.delete()

    timer.start("  map creation")
    # get / create map infos
    smap = springmaps.SpringMaps(demofile.game_setup["host"]["mapname"])
    try:
        replay.map_info = Map.objects.get(name=demofile.game_setup["host"]["mapname"])
        logger.debug("replay(%d) using existing map_info.pk=%d", replay.pk, replay.map_info.pk)
        smap.full_image_filename = MapImg.objects.get(startpostype=-1, map_info=replay.map_info).filename
        if not os.path.exists(smap.full_image_filepath):
            raise FileNotFoundError
    except (ObjectDoesNotExist, FileNotFoundError) as exc:
        # 1st time upload for this map: fetch info and full map, create thumb
        # for index page
        smap.fetch_info()
        if smap.map_info:
            startpos = str()
            for coord in smap.map_info[0]["metadata"]["StartPos"]:
                startpos += "%f,%f|" % (coord["x"], coord["z"])
            startpos = startpos[:-1]
            height = smap.map_info[0]["metadata"]["Height"]
            width = smap.map_info[0]["metadata"]["Width"]
            full_img = smap.fetch_img()
        else:
            # no result - either api.springfiles.com is down or it didn't find the map
            err = "No map info from api.springfiles.com, using empty img for map '%s'." % demofile.game_setup["host"][
                "mapname"]
            logger.error(err)
            startpos = ""
            height = 170
            width = 340
            full_img = path_join(settings.MAPS_PATH, "{}.jpg".format(smap.map_name))
            shutil.copy(path_join(settings.MAPS_PATH, "__no_map_img.jpg"), full_img)

        smap.make_home_thumb()
        if smap.map_info:
            metadata = smap.map_info[0]
        else:
            metadata = dict()
        if isinstance(exc, ObjectDoesNotExist):
            replay.map_info = Map.objects.create(name=demofile.game_setup["host"]["mapname"], startpos=startpos,
                                                 height=height, width=width, metadata2=metadata)
            MapImg.objects.create(filename=full_img, startpostype=-1, map_info=replay.map_info)
            logger.debug("replay(%d) created new map_info and MapImg: map_info.pk=%d", replay.pk, replay.map_info.pk)
            replay.save()
    #
    # startpostype = 0: Fixed            |
    # startpostype = 1: Random           |
    # startpostype = 2: ChooseInGame     | allyteam { .. startrectbottom, ... }
    # startpostype = 3: ChooseBeforeGame | team { startposx, startposz } ...
    #
    # relayhoststartpostype = 0 --> startpostype = 3
    # relayhoststartpostype = 1 --> startpostype = 3
    # relayhoststartpostype = 2 --> startpostype = 2
    # relayhoststartpostype = 3 --> startpostype = 3
    #

    # always make new img, as players will never choose exact same startpos
    try:
        mapfile = smap.create_map_with_boxes(replay)
    except:
        logger.error("FIXME: to broad exception handling.")
        logger.exception("error creating map img for Replay(%s) on map '%s'", replay.pk, replay.map_info.name)
        mapfile = "error creating map img"

    replay.map_img = MapImg.objects.create(filename=mapfile, startpostype=2, map_info=replay.map_info)
    replay.save()

    logger.debug("replay(%d) created new map_img(%d)", replay.pk, replay.map_img.pk)
    timer.stop("  map creation")

    timer.start("  tags + descriptions")
    # auto add tag 1v1 2v2 etc.
    autotag = set_autotag(replay)

    # save descriptions
    save_desc(replay, short, long_text, autotag)
    timer.stop("  tags + descriptions")

    timer.start("  demofile.additional")
    # store if demofile doesn't contain the GAMEOVER msg, because of the spring94.1 bug:
    # http://springrts.com/mantis/view.php?id=3950
    # http://springrts.com/mantis/view.php?id=3804
    if not demofile.additional["gameover_frame"]:
        logger.debug("replay(%d) has no GAMEOVER msg", replay.pk)
        AdditionalReplayInfo.objects.get_or_create(replay=replay, key="gameover", value="")

    # BAward
    if "awards" in demofile.additional:
        ba_awards, _ = BAwards.objects.get_or_create(replay=replay)
        demo_awards = demofile.additional["awards"]
        try:
            for award_name in ["ecoKillAward", "fightKillAward", "effKillAward", "cowAward", "ecoAward", "dmgRecAward",
                               "sleepAward"]:
                if type(demo_awards[award_name]) == tuple:
                    aw1, aw2, aw3 = demo_awards[award_name]
                    if aw1[0] > -1:
                        setattr(ba_awards, "{}1st".format(award_name), players[aw1[0]])
                        setattr(ba_awards, "{}1stScore".format(award_name), aw1[1])
                    else:
                        setattr(ba_awards, "{}1st".format(award_name), None)
                    if aw2[0] > -1:
                        setattr(ba_awards, "{}2nd".format(award_name), players[aw2[0]])
                        setattr(ba_awards, "{}2ndScore".format(award_name), aw2[1])
                    else:
                        setattr(ba_awards, "{}2nd".format(award_name), None)
                    if aw3[0] > -1:
                        setattr(ba_awards, "{}3rd".format(award_name), players[aw3[0]])
                        setattr(ba_awards, "{}3rdScore".format(award_name), aw3[1])
                    else:
                        setattr(ba_awards, "{}3rd".format(award_name), None)
                else:
                    if demo_awards[award_name][0] > -1:
                        setattr(ba_awards, award_name, players[demo_awards[award_name][0]])
                        setattr(ba_awards, "{}Score".format(award_name), demo_awards[award_name][1])
                    else:
                        setattr(ba_awards, award_name, None)
        except KeyError as exc:
            logger.exception('KeyError while saving BAwards: %r', exc)
        ba_awards.save()

    # XTAwards
    for xta_award in demofile.additional.get("xtawards", []):
        team = Team.objects.get(replay=replay, num=xta_award["team"])
        player = Player.objects.get(replay=replay, team=team)
        # users can get the same award multiple times for the same unit
        xt, cr = XTAwards.objects.get_or_create(replay=replay, isAlive=xta_award["isAlive"], player=player,
                                                    unit=xta_award["name"], kills=xta_award["kills"],
                                                    age=xta_award["age"])
        logger.debug("XTA award %s: %s", "created" if cr else "updated", xt)

    # cursed awards
    for teamid, cursed_awards in demofile.additional.get("cursed_awards", {}).items():
        team = Team.objects.get(replay=replay, num=teamid)
        player = Player.objects.get(replay=replay, team=team)
        clean_ca = [ca for ca in cursed_awards if hasattr(CursedAwards, ca[0])]
        ca_kwargs = dict(clean_ca)
        if set(ca[0] for ca in cursed_awards) - set(ca[0] for ca in clean_ca):
            logger.error('cursed_awards has unknown awardtype: %r', set(ca[0] for ca in cursed_awards) - set(ca[0] for ca in clean_ca))
        if ca_kwargs:
            c_a, cr = CursedAwards.objects.get_or_create(replay=replay, player=player, defaults=ca_kwargs)
            logger.debug("Cursed awards %s: %s", "created" if cr else "updated", c_a)

    timer.stop("  demofile.additional")

    pp = pprint.PrettyPrinter(depth=6)
    for k, v in demofile.additional.items():
        if k == "chat":
            v = "chat removed for shorter output"
        elif k == "awards":
            v = ba_awards
        logger.info("demofile.additional[%r]: %s", k, pp.pformat(v))

    if demofile.player_stats:
        ps, created = PlayerStats.objects.get_or_create(replay=replay, defaults={'stats': demofile.player_stats_as_jsonz()})
        logger.debug('%s %s', 'Created' if created else 'Updated', ps)
        if demofile.team_stats:
            for k, v in demofile.team_stats_as_jsonz().items():
                ts, created = TeamStats.objects.get_or_create(replay=replay, stat_type=k, defaults={'stats': v})
                logger.debug('%s %s', 'Created' if created else 'Updated', ts)
    else:
        logger.error('No player stats.')

    replay.published = True
    replay.save()
    UploadTmp.objects.filter(replay=replay).delete()
    return replay


def upload_platform_stats(demofile):
    """
    Run this *after* store_demofile_data().
    """
    try:
        client = coreapi.Client(auth=settings.PLATFORM_STATS_CREDENTIALS)
        schema = client.get(settings.PLATFORM_STATS_URL)
    except Exception as exc:
        logger.error('Cannot connect to platform stats server, when uploading stats for match %r: %s', demofile.header["gameID"], exc)
        raise
    action = ["machine", "create"]

    for pl_num, pl_data in demofile.additional['ba_platform_stats'].items():
        try:
            player = demofile.game_setup['player'][pl_num]
        except KeyError:
            logger.error('No player found for playerNum %r in BA platform stat.', pl_num)
            continue
        if player['accountid'] < 1:
            logger.warning('Not uploading platform stats for player %s (%r).', player['name'], player['accountid'])
            continue
        params = {
            'accountId': int(player['accountid']),
            'cpuName': pl_data.pop('cpuName'),
            'osFamily': pl_data.pop('osFamily'),
            'platformData': pl_data,
        }
        try:
            client.action(schema, action, params=params)
        except Exception as exc:
            logger.exception('Failed uploading platform stats for player %s (%r): %r', player['name'], player['accountid'], exc)
            raise
        logger.info('Uploaded platform stats for player %s (%r).', player['name'], player['accountid'])


def rate_match(replay):
    game = replay.game

    try:
        match_skill = get_sldb_match_skills([replay.gameID])
        if match_skill:
            match_skill = match_skill[0]
            if match_skill["status"] != 0:
                raise Exception(
                    "SLDB returned status=%d -> 1: invalid gameID value, 2: unknown or unrated gameID" % match_skill[
                        "status"])
        else:
            raise Exception("no SLDB data")
    except SLDBError as exc:
        logger.error("in get_sldb_match_skills([%r]): %s", replay.gameID, exc)
        # use "skill" tag from demo data if available
        logger.info("Trying to use skill tag from demofile")
        players = Player.objects.filter(replay=replay, spectator=False).exclude(skill="")
        if players.exists():
            replay.rated = True
            for player in players:
                pa_rating = player.account.get_rating(game, replay.match_type_short)
                demo_skill = demoskill2float(player.skill)
                if pa_rating.trueskill_mu != demo_skill:
                    pa_rating.trueskill_mu = demo_skill
                    pa_rating.save()
                if pa_rating.playername == "" or pa_rating.playername == "??":
                    pa_rating.playername = player.name
                    pa_rating.save()
                defaults = {"trueskill_mu": pa_rating.trueskill_mu,
                            "trueskill_sigma": pa_rating.trueskill_sigma,
                            "playername": player.name,
                            "match_date": replay.unixTime}
                RatingHistory.objects.update_or_create(playeraccount=player.account, match=replay, game=game,
                                                       match_type=replay.match_type_short, defaults=defaults)
        else:
            logger.info(".. no skill tags found.")
            replay.rated = False
        replay.save()
        return
    try:
        match_type = sldb_gametype2matchtype[match_skill["gameType"]]
    except:
        logger.exception("FIXME: to broad exception handling.")
        match_type = replay.match_type_short
    for player in match_skill["players"]:
        pa = player["account"]
        try:
            playername = Player.objects.get(account=pa, replay=replay).name
        except ObjectDoesNotExist:
            playername = ""
        if pa.sldb_privacy_mode != player["privacyMode"]:
            pa.sldb_privacy_mode = player["privacyMode"]
            pa.save()
        muAfter, sigmaAfter = player["skills"][1]
        globalMuAfter, globalSigmaAfter = player["skills"][3]

        pa_rating = pa.get_rating(game, match_type)
        if pa_rating.trueskill_mu != muAfter or pa_rating.trueskill_sigma != sigmaAfter:
            pa_rating.trueskill_mu = muAfter
            pa_rating.trueskill_sigma = sigmaAfter
            pa_rating.save()
        if (pa_rating.playername == "" or pa_rating.playername == "??") and playername:
            pa_rating.playername = playername
            pa_rating.save()
        defaults = {"trueskill_mu": muAfter,
                    "trueskill_sigma": sigmaAfter,
                    "playername": playername,
                    "match_date": replay.unixTime}
        RatingHistory.objects.update_or_create(playeraccount=pa, match=replay, game=game, match_type=match_type, defaults=defaults)
        pa_rating = pa.get_rating(game, "L")  # Global
        if pa_rating.trueskill_mu != globalMuAfter or pa_rating.trueskill_sigma != globalSigmaAfter:
            pa_rating.trueskill_mu = globalMuAfter
            pa_rating.trueskill_sigma = globalSigmaAfter
            pa_rating.save()
        defaults = {"trueskill_mu": globalMuAfter,
                    "trueskill_sigma": globalSigmaAfter,
                    "playername": playername,
                    "match_date": replay.unixTime}
        RatingHistory.objects.update_or_create(playeraccount=pa, match=replay, game=game, match_type="L", defaults=defaults)
    if not replay.rated:
        replay.rated = True
        replay.save()
    logger.info("Replay(%d) %s rated with values from SLDB.", replay.id, replay.gameID)


def rate_matches(replays):
    """
    Mass rating. Fetches for efficiency 32 matches at once from SLDB.
    """
    logger.info("Rating %d matches", replays.count())

    current32 = list()
    counter = 0
    for replay in replays:
        current32.append(replay)
        if counter < 31:
            counter += 1
        else:
            counter = 0
            try:
                _ = get_sldb_match_skills([r.gameID for r in current32])
            except:
                logger.exception("FIXME: to broad exception handling.")
                pass
            for match in current32:
                try:
                    rate_match(match)
                except Exception as exc:
                    logger.exception(exc)
            logger.info("done 32")
            current32 = list()


def set_accountid(player):
    if "lobbyid" in player:
        # game was on springie
        player["accountid"] = player["lobbyid"]
        return

    if "accountid" not in player or player["accountid"] is None:
        logger.info("no accountid for player '%s'", player["name"])
        # single player - we still need a unique accountid. Either we find an
        # existing player/account, or we create a temporary account.
        player["accountid"] = \
            PlayerAccount.objects.filter(player__name=player["name"], accountid__gt=0).order_by("-id").aggregate(
                Min("accountid"))['accountid__min']
        if player["accountid"]:
            logger.debug("  --> found Player with same name -> accountid=%d", player["accountid"])
        else:
            logger.debug("  --> did NOT find Player with same name")
            # didn't find an existing one, so make a temp one
            #
            # I make the accountid negative, so if the same Player pops up
            # in another replay, and has a proper accountid, it can easily
            # be noticed and corrected
            min_acc_id = PlayerAccount.objects.aggregate(Min("accountid"))['accountid__min']
            logger.debug("min_acc_id = %d", min_acc_id)
            if not min_acc_id or min_acc_id > 0:
                min_acc_id = 0
            player["accountid"] = min_acc_id - 1
        logger.info("set accountid: %d for player %s", player["accountid"], player["name"])


def save_tags(replay, tags):
    if tags:
        # strip comma separated tags and remove empty ones
        tags_ = [t.strip() for t in tags.split(",") if t.strip()]
        for tag in tags_:
            t_obj, _ = Tag.objects.get_or_create(name__iexact=tag, defaults={'name': tag})
            replay.tags.add(t_obj)


def set_autotag(replay):
    autotag = replay.match_type

    tag, created = Tag.objects.get_or_create(name=autotag, defaults={})
    if created:
        replay.tags.add(tag)
    else:
        if not replay.tags.filter(name=autotag).exists():
            replay.tags.add(tag)

    if autotag != "1v1":
        num_tag = replay.num_players
        tag, created = Tag.objects.get_or_create(name=num_tag, defaults={})
        if created:
            replay.tags.add(tag)
        else:
            if not replay.tags.filter(name=num_tag).exists():
                replay.tags.add(tag)

    return autotag


def save_desc(replay, short, long_text, autotag):
    replay.short_text = short
    replay.long_text = long_text
    if not short:
        short = "{} on {}".format(replay.match_type, replay.map_info.name)
        if replay.match_type != "1v1":
            short = "{} {}".format(replay.num_players, short)
        replay.title = short
    else:
        logger.debug("short")
        if autotag in short.split():
            replay.title = short
        else:
            replay.title = "{} {}".format(autotag, short)

    num_tag = replay.num_players
    if num_tag not in short.split():
        replay.title = "{} {}".format(num_tag, short)


def clamp(val, low, high):
    return min(high, max(low, val))


def floats2rgbhex(floats):
    rgb = ""
    for color in floats.split():
        hexstr = str(hex(clamp(int(float(color) * 255), 0, 255))[2:])
        if len(hexstr) < 2:
            hexstr = "0{}".format(hexstr)
        rgb += hexstr
    return rgb


def del_replay(replay):
    try:
        replay.map_img.delete()
    except AttributeError:
        # no image
        pass
    for tag in replay.tags.all():
        if tag.replay_count == 1 and tag.pk > 10:
            # this tag was used only by this replay and is not one of the default ones (see srs/sql/tag.sql)
            tag.delete()
    UploadTmp.objects.filter(replay=replay).delete()


def reparse(replay, path=None, tags=None, subject=None, comment=None, owner_ac=None):
    """
    Update data from stored demofile (to use new features)
    """
    path = path or path_join(replay.path, replay.filename)

    try:
        demofile = parse_demo_file.Parse_demo_file(path)
        demofile.check_magic()
        demofile.parse()
    except Exception as exc:
        logger.error("FIXME: to broad exception handling.")
        logger.exception("Error opening or parsing demofile '%s'.", path)
        raise exc
    if not replay.gameID == demofile.header["gameID"]:
        raise Exception("self.gameID(%s) != demofile.header[gameID](%s)" % (replay.gameID, demofile.header["gameID"]))
    store_demofile_data(
        demofile,
        tags or ','.join(replay.tags.all().values_list('name', flat=True)),
        path,
        subject or replay.title,
        comment or replay.long_text,
        owner_ac or replay.uploader
    )

    if 'ba_platform_stats' in demofile.additional:
        try:
            upload_platform_stats(demofile)
        except Exception as exc:
            logger.error("Error uploading platform stats for replay(%d | %s): %s", replay.id, replay, exc)
    logger.info('Finished reparse(%r).', replay)
    return replay, '0 replay at "{}"'.format(replay.get_absolute_url())
