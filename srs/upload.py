# This file is part of the "spring relay site / srs" program. It is published
# under the GPLv3.
#
# Copyright (C) 2012 Daniel Troeder (daniel #at# admin-box #dot# com)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

import logging
import os
import shutil
import stat
from tempfile import mkstemp
import datetime
import gzip
import magic
import operator

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.db.models import Min
import django.contrib.auth
from django.forms.formsets import formset_factory
from django.utils import timezone
from django.contrib.sitemaps import ping_google

from models import *
from common import all_page_infos
from forms import UploadFileForm, UploadMediaForm
import parse_demo_file
import spring_maps
from sldb import get_sldb_playerskill, get_sldb_match_skills, sldb_gametype2matchtype
from srs.sldb import demoskill2float

logger = logging.getLogger(__package__)

timer = None

class UploadTiming(object):
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
        return "\n".join([t[2]+": "+str(t[1].seconds)+"."+str(t[1].microseconds/100000) for t in self.sorted_list])

@login_required
def upload(request):
    global timer
    c = all_page_infos(request)
    UploadFormSet = formset_factory(UploadFileForm, extra=5)
    if request.method == 'POST':
        #form = UploadFileForm(request.POST, request.FILES)
        formset = UploadFormSet(request.POST, request.FILES)
        replays = []
        if formset.is_valid():
            for form in formset:
                if form.cleaned_data:
                    logger.debug("form.cleaned_data=%s", form.cleaned_data)
                    ufile = form.cleaned_data['file']
                    short = form.cleaned_data['short']
                    long_text = form.cleaned_data['long_text']
                    tags = form.cleaned_data['tags']
                    timer = UploadTiming()
                    timer.start("upload()")
                    (path, written_bytes) = save_uploaded_file(ufile.read(), ufile.name)
                    logger.info("User '%s' uploaded file '%s' with title '%s', parsing it now.", request.user, os.path.basename(path), short[:20])
        #            try:
                    if written_bytes != ufile.size:
                        return HttpResponse("Could not store the replay file. Please contact the administrator.")

                    timer.start("Parse_demo_file()")
                    demofile = parse_demo_file.Parse_demo_file(path)
                    timer.stop("Parse_demo_file()")
                    try:
                        demofile.check_magic()
                    except:
                        form._errors = {'file': [u'Not a spring demofile: %s.'%ufile.name]}
                        replays.append((False, 'Not a spring demofile: %s.'%ufile.name))
                        continue

                    timer.start("parse()")
                    demofile.parse()
                    timer.stop("parse()")

                    try:
                        replay = Replay.objects.get(gameID=demofile.header["gameID"])
                        if replay.was_succ_uploaded:
                            logger.info("Replay already existed: pk=%d gameID=%s", replay.pk, replay.gameID)
                            form._errors = {'file': [u'Uploaded replay already exists: "%s"'%replay.title]}
                            replays.append((False, 'Uploaded replay already exists: <a href="%s">%s</a>.'%(replay.get_absolute_url(), replay.title)))
                        else:
                            logger.info("Deleting existing unsuccessfully uploaded replay '%s' (%d, %s)", replay, replay.pk, replay.gameID)
                            del_replay(replay)
                            replays.append((False, "Error while uploading."))
                        continue
                    except:
                        new_filename = os.path.basename(path).replace(" ", "_")
                        newpath = settings.REPLAYS_PATH+"/"+new_filename
                        shutil.move(path, newpath)
                        os.chmod(newpath, stat.S_IRUSR|stat.S_IWUSR|stat.S_IRGRP|stat.S_IWGRP|stat.S_IROTH)
                        timer.start("store_demofile_data()")
                        replay = store_demofile_data(demofile, tags, newpath, ufile.name, short, long_text, request.user)
                        timer.stop("store_demofile_data()")
                        demofile = tags = newpath = ufile = short = long_text = None
                        replays.append((True, replay))
                        logger.info("New replay created: pk=%d gameID=%s", replay.pk, replay.gameID)

                        try:
                            timer.start("rate_match()")
                            rate_match(replay)
                        except Exception, e:
                            logger.error("Error rating replay(%d | %s): %s", replay.id, replay, e)
                        finally:
                            timer.stop("rate_match()")

                        try:
                            timer.start("ping_google()")
                            ping_google()
                        except Exception, e:
                            logger.exception("ping_google(): %s", e)
                            pass
                        finally:
                            timer.stop("ping_google()")

                    timer.stop("upload()")
                    logger.info("timings:\n%s", timer)

        if len(replays) == 0:
            logger.error("no replay created, this shouldn't happen")
        elif len(replays) == 1:
            if replays[0][0]:
                return HttpResponseRedirect(replays[0][1].get_absolute_url())
            else:
                # fall through to get back on page with error msg
                pass
        else:
            c['replays'] = replays
            c["replay_details"] = True
            return render_to_response('multi_upload_success.html', c, context_instance=RequestContext(request))
    else:
        #form = UploadFileForm()
        formset = UploadFormSet()
    c['formset'] = formset
    return render_to_response('upload.html', c, context_instance=RequestContext(request))

def xmlrpc_upload(username, password, filename, demofile, subject, comment, tags, owner):
    global timer
    logger.info("username='%s' password=xxxxxx filename='%s' subject='%s' comment='%s' tags='%s' owner='%s'", username, filename, subject, comment, tags, owner)

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
    except:
        logger.info("Owner '%s' unknown on replays site, abort.", owner)
        return "2 Unknown or inactive owner account, please log in via web interface once."

    timer = UploadTiming()
    timer.start("xmlrpc_upload()")
    # this is code double from upload() :(
    (path, written_bytes) = save_uploaded_file(demofile.data, filename)
    logger.info("User '%s' uploaded file '%s' with title '%s', parsing it now.", username, path, subject)

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
            logger.info("Replay already existed: pk=%d gameID=%s", replay.pk, replay.gameID)
            try:
                os.remove(path)
            except:
                logger.error("Could not remove file '%s'", path)
            return '3 uploaded replay already exists as "%s" at "%s"'%(replay.__unicode__(), replay.get_absolute_url())
        else:
            logger.info("Deleting existing unsuccessfully uploaded replay '%s' (%d, %s)", replay, replay.pk, replay.gameID)
            del_replay(replay)
    except:
        pass

    new_filename = os.path.basename(path).replace(" ", "_")
    newpath = settings.REPLAYS_PATH+"/"+new_filename
    shutil.move(path, newpath)
    os.chmod(newpath, stat.S_IRUSR|stat.S_IWUSR|stat.S_IRGRP|stat.S_IWGRP|stat.S_IROTH)
    try:
        timer.start("store_demofile_data()")
        replay = store_demofile_data(demofile, tags, newpath, new_filename, subject, comment, owner_ac)
    except Exception, e:
        logger.error("Error in store_demofile_data(): %s", e)
        return "4 server error, please try again later, or contact admin"
    finally:
        timer.stop("store_demofile_data()")

    logger.info("New replay created: pk=%d gameID=%s", replay.pk, replay.gameID)
    try:
        timer.start("rate_match()")
        rate_match(replay)
    except Exception, e:
        logger.error("Error rating replay(%d | %s): %s", replay.id, replay, e)
    finally:
        timer.stop("rate_match()")

    try:
        timer.start("ping_google()")
        ping_google()
    except Exception:
        logger.exception("ping_google(): %s", e)
        pass
    finally:
        timer.stop("ping_google()")

    timer.stop("xmlrpc_upload()")
    logger.info("timings:\n%s", timer)

    return '0 received %d bytes, replay at "%s"'%(written_bytes, replay.get_absolute_url())

def save_uploaded_file(ufile, filename):
    """
    may raise an exception from os.open/write/close()
    """
    suff = filename.split("_")[-1]
    (fd, path) = mkstemp(suffix="_"+suff+".gz", prefix=filename[:-len(suff)-1]+"__")
    gzf = gzip.GzipFile(filename=None, mode="wb", compresslevel=6, fileobj=os.fdopen(fd, "wb"))
    written_bytes = gzf.write(ufile)
    gzf.close()
    logger.debug("stored file with '%d' bytes in '%s'", written_bytes, path)
    return (path, written_bytes)

def store_demofile_data(demofile, tags, path, filename, short, long_text, user):
    """
    Store all data about this replay in the database
    """
    replay = Replay()
    replay.published = False
    replay.uploader = user
    replay.title = short # temp

    # copy match infos 
    for key in ["versionString", "gameID", "wallclockTime"]:
        replay.__setattr__(key, demofile.header[key])
    replay.unixTime = datetime.datetime.strptime(demofile.header["unixTime"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.get_current_timezone())
    for key in ["autohostname", "gametype", "startpostype"]:
        if demofile.game_setup["host"].has_key(key):
            replay.__setattr__(key, demofile.game_setup["host"][key])

    replay.filename       = os.path.basename(path)
    replay.path           = os.path.dirname(path)
    replay.download_count = 0

    replay.save()
    uploadtmp = UploadTmp.objects.create(replay=replay)

    logger.debug("replay(%d) gameID='%s' unixTime='%s' created", replay.pk, replay.gameID, replay.unixTime)

    # save AllyTeams
    timer.start("  allyteams")
    allyteams = {}
    for num,val in demofile.game_setup['allyteam'].items():
        allyteam = Allyteam()
        allyteams[num] = allyteam
        for k,v in val.items():
            allyteam.__setattr__(k, v)
        allyteam.replay = replay
        allyteam.winner = int(num) in demofile.winningAllyTeams
        allyteam.save()
    timer.stop("  allyteams")

    logger.debug("replay(%d) allyteams=%s", replay.pk, [a.pk for a in allyteams.values()])

    # if match is <2 min long, don't rate it
    replay.notcomplete = demofile.header['gameTime'].startswith("0:00:") or demofile.header['gameTime'].startswith("0:01:")
    demofile.header = None

    timer.start("  map creation")
    # get / create map infos
    try:
        replay.map_info = Map.objects.get(name=demofile.game_setup["host"]["mapname"])
        logger.debug("replay(%d) using existing map_info.pk=%d", replay.pk, replay.map_info.pk)
    except:
        # 1st time upload for this map: fetch info and full map, create thumb
        # for index page
        smap = spring_maps.Spring_maps(demofile.game_setup["host"]["mapname"])
        smap.fetch_info()
        if smap.map_info:
            startpos = str()
            for coord in smap.map_info[0]["metadata"]["StartPos"]:
                startpos += "%f,%f|"%(coord["x"], coord["z"])
            startpos = startpos[:-1]
            height   = smap.map_info[0]["metadata"]["Height"]
            width    = smap.map_info[0]["metadata"]["Width"]
            full_img = smap.fetch_img()
        else:
            # no result - either api.springfiles.com is down or it didn't find the map
            err = "No map info from api.springfiles.com, using empty img for map '%s'."%demofile.game_setup["host"]["mapname"]
            logger.error(err)
            startpos = ""
            height   = 170
            width    = 340
            shutil.copy(settings.MAPS_PATH+"__no_map_img.jpg", settings.MAPS_PATH+smap.mapname+".jpg")
            full_img = settings.MAPS_PATH+smap.mapname+".jpg"

        smap.make_home_thumb()
        replay.map_info = Map.objects.create(name=demofile.game_setup["host"]["mapname"], startpos=startpos, height=height, width=width)
        MapImg.objects.create(filename=full_img, startpostype=-1, map_info=replay.map_info)
        logger.debug("replay(%d) created new map_info and MapImg: map_info.pk=%d", replay.pk, replay.map_info.pk)

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

    # get / create map thumbs
    startpos = demofile.game_setup["host"]["startpostype"]
    logger.debug("replay(%d) startpostype=%d", replay.pk, startpos)
    if startpos == 0 or startpos == 1 or startpos == 3:
        # fixed start positions
        try:
            replay.map_img = MapImg.objects.get(map_info = replay.map_info, startpostype=1)
            logger.debug("replay(%d) using existing map_img.pk=%d", replay.pk, replay.map_img.pk)
        except:
            mapfile = spring_maps.create_map_with_positions(replay.map_info)
            replay.map_img = MapImg.objects.create(filename=mapfile, startpostype=1, map_info=replay.map_info)
            logger.debug("replay(%d) created new map_img.pk=%d", replay.pk, replay.map_img.pk)
    elif startpos == 2:
        # start boxes
        # look for replays with the same map and start boxes
        replay_same_map_n_boxes = Replay.objects.filter(map_info__name=replay.map_info.name).exclude(id=replay.id)
        for at in Allyteam.objects.filter(replay=replay):
            if at.startrectbottom != None and at.startrectleft != None and at.startrectright != None and at.startrecttop != None:
                replay_same_map_n_boxes = replay_same_map_n_boxes.filter(allyteam__startrectbottom=at.startrectbottom, allyteam__startrectleft=at.startrectleft, allyteam__startrectright=at.startrectright, allyteam__startrecttop=at.startrecttop)
            else:
                replay_same_map_n_boxes = Replay.objects.none()
        if replay_same_map_n_boxes.exists():
            # found at least one replay with the same map and the same boxes
            # make sure the number of boxes match
            for replay_smnb in replay_same_map_n_boxes:
                if replay_smnb.allyteam_set.count() == replay.allyteam_set.count():
                    replay.map_img = replay_smnb.map_img
                    logger.debug("replay(%d) using existing map_img(%d) from replay(pk=%d, gameID=%s)", replay.pk, replay_smnb.map_img.pk, replay_smnb.pk, replay_smnb.gameID)
                    break
        if not replay.map_img:
            # didn't find an existing map_img before
            try:
                mapfile = spring_maps.create_map_with_boxes(replay)
            except Exception, e:
                logger.error("error creating map img: %s", e)
                mapfile = "error creating map img"

            replay.map_img = MapImg.objects.create(filename=mapfile, startpostype=2, map_info=replay.map_info)
            logger.debug("replay(%d) created new map_img.pk=%d", replay.pk, replay.map_img.pk)
    else:
        logger.debug("replay(%d) startpostype '%d' not supported", replay.pk, startpos)
        raise Exception("startpostype '%d' not supported"%startpos)

    timer.stop("  map creation")

    # save tags
    save_tags(replay, tags)

    # save map and mod options
    def truncate_option(k, v):
        if len(str(k)) > 512: k = "string to long, sorry"
        if len(str(v)) > 512: v = "string to long, sorry"
        return k, v

    timer.start("  map+modoptions")
    for k,v in demofile.game_setup['mapoptions'].items():
        k,v = truncate_option(k, v)
        MapOption.objects.create(name=k, value=v, replay=replay)

    for k,v in demofile.game_setup['modoptions'].items():
        k,v = truncate_option(k, v)
        ModOption.objects.create(name=k, value=v, replay=replay)
    timer.stop("  map+modoptions")

    logger.debug("replay(%d) added tags (%s), mapoptions and modoptions", replay.pk, replay.tags.all().values_list("name"))

    # save players and their accounts
    timer.start("  players and playeraccounts")
    players = {}
    teams = []
    for pnum,player in demofile.game_setup['player'].items():
        set_accountid(player)
        pa, _ = PlayerAccount.objects.get_or_create(accountid=player["accountid"], defaults={'countrycode': player["countrycode"], 'preffered_name': player["name"]})
        if pa.preffered_name == "??" or pa.preffered_name == "":
            pa.preffered_name = player["name"]
            pa.save()
        if pa.countrycode == "??":
            pa.countrycode    = player["countrycode"]
            pa.save()
        try:
            skill = player["skill"]
        except:
            skill = ""
        try:
            skilluncertainty = player["skilluncertainty"]
        except:
            skilluncertainty = -1
        players[pnum] = Player.objects.create(account=pa, name=player["name"], rank=player["rank"], skill=skill, skilluncertainty=skilluncertainty, spectator=bool(player["spectator"]), replay=replay)
        if pa.accountid > 0:
            # if we found players w/o account, and now have a player with the
            # same name, but with an account - unify them
            pac = Player.objects.filter(name=player["name"], account__accountid__lt=0)
            if pac.exists():
                logger.info("replay(%d) found matching name-account info for previously accountless player(s):", replay.pk)
                logger.info("replay(%d) PA.pk=%d Player(s).pk:%s", replay.pk, pa.pk, [(p.name, p.pk) for p in pac])
                for pplayer in pac:
                    pplayer.account.delete()
                    pplayer.account = pa
                    pplayer.save()

        if player.has_key("team") and player["team"] != None:
            teams.append((players[pnum], player["team"])) # [(Player, "2"), ...]

            if player.has_key("startposx") and player.has_key("startposy") and player.has_key("startposz"):
                players[pnum].startposx = player["startposx"]
                players[pnum].startposy = player["startposy"]
                players[pnum].startposz = player["startposz"]
                players[pnum].save()
            else:
                logger.error("player has no start coords. player: %s players[%d]: %s", player, pnum, players[pnum])
        else:
            # this must be a spectator
            if not player["spectator"] == 1:
                logger.error("replay(%d) found player without team and not a spectator: %s", replay.pk, player)

    timer.stop("  players and playeraccounts")
    logger.debug("replay(%d) teams=%s", replay.pk, teams)

    logger.debug("replay(%d) saved Players(%s) and PlayerAccounts", replay.pk, Player.objects.filter(replay=replay).values_list('id', 'name'))

    # save teams
    timer.start("  teams")
    for tnum,val in demofile.game_setup['team'].items():
        team = Team()
        for k,v in val.items():
            if k == "allyteam":
                team.allyteam = allyteams[v]
            elif k == "teamleader":
                team.teamleader = players[v]
            elif k =="rgbcolor":
                team.rgbcolor = floats2rgbhex(v)
            else:
                team.__setattr__(k, v)
        team.replay = replay
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
            Player.objects.create(account=bot_pa, name="Bot (of "+team.teamleader.name+")", rank=1, spectator=False, team=team, replay=replay)

            # add a "Bot" tag
            bottag, _ = Tag.objects.get_or_create(name = "Bot", defaults={})
            replay.tags.add(bottag)

            # detect single player and add tag
            if demofile.game_setup["host"].has_key("hostip") and demofile.game_setup["host"]["hostip"] == "" and demofile.game_setup["host"]["ishost"] == 1:
                sptag, _ = Tag.objects.get_or_create(name = "Single Player", defaults={})
                replay.tags.add(sptag)
    timer.stop("  teams")
    logger.debug("replay(%d) saved Teams (%s)", replay.pk, Team.objects.filter(replay=replay).values_list('id'))

    # work around Zero-Ks usage of useless AllyTeams
    ats = Allyteam.objects.filter(replay=replay, team__isnull=True)
    if ats.exists():
        logger.debug("replay(%d) deleting useless AllyTeams:%s", replay.pk, ats)
        ats.delete()

    timer.start("  tags + descriptions")
    # auto add tag 1v1 2v2 etc.
    autotag = set_autotag(replay)

    # save descriptions
    save_desc(replay, short, long_text, autotag)
    timer.stop("  tags + descriptions")

    # store if demofile doesn't contain the GAMEOVER msg, because of the spring94.1 bug:
    # http://springrts.com/mantis/view.php?id=3950
    # http://springrts.com/mantis/view.php?id=3804
    if not demofile.additional["gameover_frame"]:
        logger.debug("replay(%d) has no GAMEOVER msg", replay.pk)
        AdditionalReplayInfo.objects.create(replay=replay, key="gameover", value="")

    if demofile.additional.has_key("awards"):
        ba_awards = BAwards(replay=replay)
        demo_awards = demofile.additional["awards"]
        for award_name in ["ecoKillAward", "fightKillAward", "effKillAward", "cowAward", "ecoAward", "dmgRecAward", "sleepAward"]:
            if type(demo_awards[award_name]) == tuple:
                aw1, aw2, aw3 = demo_awards[award_name]
                if aw1 > -1:
                    setattr(ba_awards, award_name+"1st", players[aw1])
                if aw2 > -1:
                    setattr(ba_awards, award_name+"2nd", players[aw2])
                if aw3 > -1:
                    setattr(ba_awards, award_name+"3rd", players[aw3])
            else:
                if demo_awards[award_name] > -1:
                    setattr(ba_awards, award_name, players[demo_awards[award_name]])
        ba_awards.save()
        logger.debug("replay(%d) has BAwards(%d): %s", replay.pk, ba_awards.pk, ba_awards)

    replay.published = True
    replay.save()
    uploadtmp.delete()
    return replay

def rate_match(replay):
    game = replay.game

    try:
        match_skill = get_sldb_match_skills([replay.gameID])
        if match_skill:
            match_skill = match_skill[0]
            if match_skill["status"] != 0:
                raise Exception("SLDB returned status=%d -> 1: invalid gameID value, 2: unknown or unrated gameID"%match_skill["status"])
        else:
            raise Exception("no SLDB data")
    except Exception, e:
        logger.debug("in/after get_sldb_match_skills(): %s", e)
        # use "skill" tag from demo data if available
        logger.info("Trying to use skill tag from demofile")
        players = Player.objects.filter(replay=replay, spectator=False).exclude(skill="").prefetch_related("account")
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
                rh, created = RatingHistory.objects.get_or_create(playeraccount=player.account, match=replay, game=game, match_type=replay.match_type_short, defaults=defaults)
                if not created:
                    save_it = False
                    for k,v in defaults.items():
                        if getattr(rh, k) != v:
                            setattr(rh, k, v)
                            save_it = True
                    if save_it:
                        rh.save()
        else:
            logger.info(".. no skill tags found.")
            replay.rated = False
        replay.save()
        return
    try:
        match_type = sldb_gametype2matchtype[match_skill["gameType"]]
    except:
        match_type = replay.match_type_short
    for player in match_skill["players"]:
        pa = player["account"]
        try:
            playername = Player.objects.get(account=pa, replay=replay).name
        except:
            playername = ""
        if pa.sldb_privacy_mode != player["privacyMode"]:
            pa.sldb_privacy_mode = player["privacyMode"]
            pa.save()
        muAfter      , sigmaAfter       = player["skills"][1]
        globalMuAfter, globalSigmaAfter = player["skills"][3]

        pa_rating = pa.get_rating(game, match_type)
        if pa_rating.trueskill_mu != muAfter or pa_rating.trueskill_sigma != sigmaAfter:
            pa_rating.trueskill_mu    = muAfter
            pa_rating.trueskill_sigma = sigmaAfter
            pa_rating.save()
        if (pa_rating.playername == "" or pa_rating.playername == "??") and playername:
            pa_rating.playername = playername
            pa_rating.save()
        defaults = {"trueskill_mu": muAfter,
                    "trueskill_sigma": sigmaAfter,
                    "playername": playername,
                    "match_date": replay.unixTime}
        rh, created = RatingHistory.objects.get_or_create(playeraccount=pa, match=replay, game=game, match_type=match_type, defaults=defaults)
        if not created:
            save_it = False
            for k,v in defaults.items():
                if getattr(rh, k) != v:
                    setattr(rh, k, v)
                    save_it = True
            if save_it:
                rh.save()
        pa_rating = pa.get_rating(game, "L") # Global
        if pa_rating.trueskill_mu != globalMuAfter or pa_rating.trueskill_sigma != globalSigmaAfter:
            pa_rating.trueskill_mu    = globalMuAfter
            pa_rating.trueskill_sigma = globalSigmaAfter
            pa_rating.save()
        defaults = {"trueskill_mu": globalMuAfter,
                    "trueskill_sigma": globalSigmaAfter,
                    "playername": playername,
                    "match_date": replay.unixTime}
        rh, created = RatingHistory.objects.get_or_create(playeraccount=pa, match=replay, game=game, match_type="L", defaults=defaults)
        if not created:
            save_it = False
            for k,v in defaults.items():
                if getattr(rh, k) != v:
                    setattr(rh, k, v)
                    save_it = True
            if save_it:
                rh.save()
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
            except Exception, e:
                logger.exception(e)
            for match in current32:
                try:
                    rate_match(match)
                except Exception, e:
                    logger.exception(e)
            logger.info("done 32")
            current32 = list()

def set_accountid(player):
    if player.has_key("lobbyid"):
        # game was on springie
        player["accountid"] = player["lobbyid"]

    if not player.has_key("accountid"):
        logger.debug("v.has_key(accountid)==False")
        # single player - we still need a unique accountid. Either we find an
        # existing player/account, or we create a temporary account.
        player["accountid"] = PlayerAccount.objects.filter(player__name=player["name"], accountid__gt=0).aggregate(Min("accountid"))['accountid__min']
        if player["accountid"]:
            logger.debug("v.has_key(accountid)==False -> found Player with same name -> accountid=%d", player["accountid"])
        else:
            logger.debug("v.has_key(accountid)==False -> did NOT find Player with same name")
            # didn't find an existing one, so make a temp one
            #
            # I make the accountid negative, so if the same Player pops up
            # in another replay, and has a proper accountid, it can easily
            # be noticed and corrected
            min_acc_id = PlayerAccount.objects.aggregate(Min("accountid"))['accountid__min']
            logger.debug("min_acc_id = %d", min_acc_id)
            if not min_acc_id or min_acc_id > 0: min_acc_id = 0
            player["accountid"] = min_acc_id-1
            logger.debug("v[accountid] = %d", player["accountid"])

def save_tags(replay, tags):
    if tags:
        # strip comma separated tags and remove empty ones
        tags_ = [t.strip() for t in tags.split(",") if t.strip()]
        for tag in tags_:
            t_obj, _ = Tag.objects.get_or_create(name__iexact = tag, defaults={'name': tag})
            replay.tags.add(t_obj)

def set_autotag(replay):
    autotag = replay.match_type

    tag, created = Tag.objects.get_or_create(name = autotag, defaults={})
    if created:
        replay.tags.add(tag)
    else:
        if not replay.tags.filter(name=autotag).exists():
            replay.tags.add(tag)

    if autotag != "1v1":
        num_tag = replay.num_players
        tag, created = Tag.objects.get_or_create(name = num_tag, defaults={})
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
        short = "%s on %s"%(replay.match_type, replay.map_info.name)
        if replay.match_type != "1v1":
            short = replay.num_players + " " + short
        replay.title = short
    else:
        logger.debug("short")
        if autotag in short.split():
            replay.title = short
        else:
            replay.title = autotag+" "+short

    num_tag = replay.num_players
    if num_tag not in short.split():
        replay.title = num_tag+" "+short

def clamp(val, low, high):
    return min(high, max(low, val))

def floats2rgbhex(floats):
    rgb = ""
    for color in floats.split():
        hexstr = str(hex(clamp(int(float(color)*255), 0, 255))[2:])
        if len(hexstr) < 2:
            hexstr = "0"+hexstr
        rgb += hexstr
    return rgb

def del_replay(replay):
    replay.map_img.delete()
    for tag in replay.tags.all():
        if tag.replays() == 1 and tag.pk > 10:
            # this tag was used only by this replay and is not one of the default ones (see srs/sql/tag.sql)
            tag.delete()
    UploadTmp.objects.filter(replay=replay).delete()

@login_required
def upload_media(request, gameID):
    c = all_page_infos(request)

    replay = get_object_or_404(Replay, gameID=gameID)
    if not request.user in get_owner_list(replay.uploader):
        return HttpResponseRedirect(replay.get_absolute_url())

    UploadMediaFormSet = formset_factory(UploadMediaForm, extra=5)
    c["replay"] = replay
    c["replay_details"] = True

    if request.method == 'POST':
        logger.debug("request.FILES: %s", request.FILES)
        formset = UploadMediaFormSet(request.POST, request.FILES)
        if formset.is_valid():
            c["media_files"] = list()
            for form in formset:
                if form.cleaned_data:
                    logger.info("form.cleaned_data=%s", form.cleaned_data)
                    media = form.cleaned_data['media_file']
                    image = form.cleaned_data['image_file']
                    comment=form.cleaned_data['comment']
                    if media:
                        media.seek(0)
                        media_magic_text = magic.from_buffer(media.read(1024))
                        media.seek(0)
                        media_magic_mime = magic.from_buffer(media.read(1024), mime=True)
                        media.seek(0)
                    else:
                        media_magic_text = None
                        media_magic_mime = None
                    erm = ExtraReplayMedia.objects.create(replay=replay, uploader=request.user, comment=comment, media=media, image=image, media_magic_text=media_magic_text, media_magic_mime=media_magic_mime)
                    c["media_files"].append(erm)
                    logger.info("User '%s' uploaded for replay:'%s' media:'%s' img:'%s' with comment:'%s'.", request.user, replay, erm.media, erm.image, erm.comment[:20])
            return render_to_response('upload_media_success.html', c, context_instance=RequestContext(request))
        else:
            logger.error("formset.errors: %s", formset.errors)
            logger.error("request.FILES: %s", request.FILES)
            logger.error("request.POST: %s", request.POST)
    else:
        formset = UploadMediaFormSet()
    c["formset"] = formset
    return render_to_response('upload_media.html', c, context_instance=RequestContext(request))
