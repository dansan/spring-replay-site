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

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.db.models import Min
import django.contrib.auth
from django.forms.formsets import formset_factory

from models import *
from common import all_page_infos
from forms import UploadFileForm
import parse_demo_file
import spring_maps
from rating import rate_match


logger = logging.getLogger(__package__)

@login_required
def upload(request):
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
                    (path, written_bytes) = save_uploaded_file(ufile.read(), ufile.name)
                    logger.info("User '%s' uploaded file '%s' with title '%s', parsing it now.", request.user, os.path.basename(path), short[:20])
        #            try:
                    if written_bytes != ufile.size:
                        return HttpResponse("Could not store the replay file. Please contact the administrator.")

                    demofile = parse_demo_file.Parse_demo_file(path)
                    try:
                        demofile.check_magic()
                    except:
                        form._errors = {'file': [u'Not a spring demofile: %s.'%ufile.name]}
                        replays.append((False, 'Not a spring demofile: %s.'%ufile.name))
                        continue
                    demofile.parse()

                    try:
                        replay = Replay.objects.get(gameID=demofile.header["gameID"])
                        if replay.was_succ_uploaded():
                            logger.info("Replay already existed: pk=%d gameID=%s", replay.pk, replay.gameID)
                            form._errors = {'file': [u'Uploaded replay already exists: "%s"'%replay.title]}
                            replays.append((False, 'Uploaded replay already exists: <a href="%s">%s</a>.'%(replay.get_absolute_url(), replay.title)))
                        else:
                            logger.info("Deleting existing unsuccessfully uploaded replay '%s' (%d, %s)", replay, replay.pk, replay.gameID)
                            del_replay(replay)
                            replays.append((False, "Error while uploading."))
                        continue
                    except:
                        shutil.move(path, settings.MEDIA_ROOT)
                        os.chmod(settings.MEDIA_ROOT+os.path.basename(path), stat.S_IRUSR|stat.S_IWUSR|stat.S_IRGRP|stat.S_IWGRP|stat.S_IROTH)
                        replay = store_demofile_data(demofile, tags, settings.MEDIA_ROOT+os.path.basename(path), ufile.name, short, long_text, request.user)
                        replays.append((True, replay))
                        logger.info("New replay created: pk=%d gameID=%s", replay.pk, replay.gameID)
                        try:
                            rate_match(replay)
                        except Exception, e:
                            logger.error("Error rating replay(%d | %s): %s", replay.id, replay, e)
        #            except Exception, e:
        #                return HttpResponse("The was a problem with the upload: %s<br/>Please retry or contact the administrator.<br/><br/><a href="/">Home</a>"%e)
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

    # this is code double from upload() :(
    (path, written_bytes) = save_uploaded_file(demofile.data, filename)
    logger.info("User '%s' uploaded file '%s' with title '%s', parsing it now.", username, path, subject)

    demofile = parse_demo_file.Parse_demo_file(path)
    demofile.check_magic()
    demofile.parse()

    try:
        replay = Replay.objects.get(gameID=demofile.header["gameID"])
        if replay.was_succ_uploaded():
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

    shutil.move(path, settings.MEDIA_ROOT)
    newpath = settings.MEDIA_ROOT+os.path.basename(path)
    os.chmod(newpath, stat.S_IRUSR|stat.S_IWUSR|stat.S_IRGRP|stat.S_IWGRP|stat.S_IROTH)
    try:
        replay = store_demofile_data(demofile, tags, newpath, filename, subject, comment, user)
        replay.uploader = owner_ac
        replay.save()
    except Exception, e:
        logger.error("Error in store_demofile_data(): %s", e)
        return "4 server error, please try again later, or contact admin"

    logger.info("New replay created: pk=%d gameID=%s", replay.pk, replay.gameID)
    try:
        rate_match(replay)
    except Exception, e:
        logger.error("Error rating replay(%d | %s): %s", replay.id, replay, e)
    return '0 received %d bytes, replay at "%s"'%(written_bytes, replay.get_absolute_url())

def save_uploaded_file(ufile, filename):
    """
    may raise an exception from os.open/write/close()
    """
    suff = filename.split("_")[-1]
    (fd, path) = mkstemp(suffix="_"+suff, prefix=filename[:-len(suff)-1]+"__")
    written_bytes = os.write(fd, ufile)
    os.close(fd)
    logger.debug("stored file with '%d' bytes in '%s'", written_bytes, path)
    return (path, written_bytes)

def store_demofile_data(demofile, tags, path, filename, short, long_text, user):
    """
    Store all data about this replay in the database
    """
    replay = Replay()
    replay.uploader = user
    replay.title = short # temp

    # copy match infos 
    for key in ["versionString", "gameID", "wallclockTime"]:
        replay.__setattr__(key, demofile.header[key])
    replay.unixTime = datetime.datetime.strptime(demofile.header["unixTime"], "%Y-%m-%d %H:%M:%S")
    for key in ["autohostname", "gametype", "startpostype"]:
        if demofile.game_setup["host"].has_key(key):
            replay.__setattr__(key, demofile.game_setup["host"][key])

    # the replay file
    replay.replayfile = ReplayFile.objects.create(filename=os.path.basename(path), path=os.path.dirname(path), ori_filename=filename, download_count=0)

    replay.save()
    uploadtmp = UploadTmp.objects.create(replay=replay)

    logger.debug("replay(%d) gameID='%s' unixTime='%s' created", replay.pk, replay.gameID, replay.unixTime)

    # save AllyTeams
    allyteams = {}
    for num,val in demofile.game_setup['allyteam'].items():
        allyteam = Allyteam()
        allyteams[num] = allyteam
        for k,v in val.items():
            allyteam.__setattr__(k, v)
        allyteam.replay = replay
        allyteam.winner = int(num) in demofile.winningAllyTeams
        allyteam.save()

    logger.debug("replay(%d) allyteams=%s", replay.pk, [a.pk for a in allyteams.values()])

    # winner known?
    replay.notcomplete = demofile.header['winningAllyTeamsSize'] == 0

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

    replay.save()

    # save tags
    save_tags(replay, tags)
    replay.save()

    # save map and mod options
    for k,v in demofile.game_setup['mapoptions'].items():
        MapOption.objects.create(name=k, value=v, replay=replay)

    for k,v in demofile.game_setup['modoptions'].items():
        ModOption.objects.create(name=k, value=v, replay=replay)

    logger.debug("replay(%d) added tags (%s), mapoptions and modoptions", replay.pk, replay.tags.all().values_list("name"))

    # save players and their accounts
    players = {}
    teams = []
    for pnum,player in demofile.game_setup['player'].items():
        set_accountid(player)
        pa, _ = PlayerAccount.objects.get_or_create(accountid=player["accountid"], defaults={'accountid': player["accountid"], 'countrycode': player["countrycode"], 'preffered_name': player["name"]})
        players[pnum] = Player.objects.create(account=pa, name=player["name"], rank=player["rank"], spectator=bool(player["spectator"]), replay=replay)
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

        if player.has_key("team"):
            teams.append((players[pnum], str(player["team"]))) # [(Player, "2"), ...]
        else:
            # this must be a spectator
            if not player["spectator"] == 1:
                logger.error("replay(%d) found player without team and not a spectator: %s", replay.pk, player)

    logger.debug("replay(%d) teams=%s", replay.pk, teams)

    logger.debug("replay(%d) saved Players(%s) and PlayerAccounts", replay.pk, Player.objects.filter(replay=replay).values_list('id', 'name'))

    # save teams
    for tnum,val in demofile.game_setup['team'].items():
        team = Team()
        for k,v in val.items():
            if k == "allyteam":
                team.allyteam = allyteams[str(v)]
            elif k == "teamleader":
                team.teamleader = players[str(v)]
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
            bottag, _ = Tag.objects.get_or_create(name = "Bot", defaults={'name': "Bot"})
            replay.tags.add(bottag)

            # detect single player and add tag
            if demofile.game_setup["host"].has_key("hostip") and demofile.game_setup["host"]["hostip"] == "" and demofile.game_setup["host"]["ishost"] == 1:
                sptag, _ = Tag.objects.get_or_create(name = "Single Player", defaults={'name': "Single Player"})
                replay.tags.add(sptag)

    logger.debug("replay(%d) saved Teams (%s)", replay.pk, Team.objects.filter(replay=replay).values_list('id'))

    # work around Zero-Ks usage of useless AllyTeams
    ats = Allyteam.objects.filter(replay=replay, team__isnull=True)
    if ats.exists():
        logger.debug("replay(%d) deleting useless AllyTeams:%s", replay.pk, ats)
        ats.delete()

    # auto add tag 1v1 2v2 etc.
    autotag = set_autotag(replay)

    # save descriptions
    save_desc(replay, short, long_text, autotag)

    replay.save()
    uploadtmp.delete()

    return replay


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
    autotag = ""
    if Allyteam.objects.filter(replay=replay).count() > 3:
        autotag = "FFA"
    else:
        for at in Allyteam.objects.filter(replay=replay):
            autotag += str(Team.objects.filter(allyteam=at).count())+"v"
        autotag = autotag[:-1]

    tag, created = Tag.objects.get_or_create(name = autotag, defaults={'name': autotag})
    if created:
        replay.tags.add(tag)
    else:
        if not replay.tags.filter(name=autotag).exists():
            replay.tags.add(tag)
    return autotag

def save_desc(replay, short, long_text, autotag):
    replay.short_text = short
    replay.long_text = long_text
    if autotag in short:
        replay.title = short
    else:
        replay.title = autotag+" "+short

def clamp(val, low, high):
    return min(high, max(low, val))

def floats2rgbhex(floats):
    rgb = ""
    for color in floats.split():
        rgb += str(hex(clamp(int(float(color)*256), 0, 256))[2:])
    return rgb

def del_replay(replay):
    replay.replayfile.delete()
    replay.map_img.delete()
    for tag in replay.tags.all():
        if tag.replays() == 1 and tag.pk > 10:
            # this tag was used only by this replay and is not one of the default ones (see srs/sql/tag.sql)
            tag.delete()
    UploadTmp.objects.filter(replay=replay).delete()
