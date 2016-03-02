# This file is part of the "spring relay site / srs" program. It is published
# under the GPLv3.
#
# Copyright (C) 2012 Daniel Troeder (daniel #at# admin-box #dot# com)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

import logging
import shutil
import stat
import magic

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.forms.formsets import formset_factory
from django.contrib.sitemaps import ping_google

from upload import UploadTiming, store_demofile_data, save_uploaded_file, del_replay, rate_match
from models import *
from common import all_page_infos
from forms import UploadFileForm, UploadMediaForm
import parse_demo_file

logger = logging.getLogger(__package__)

timer = None

@login_required
def upload(request):
    global timer
    c = all_page_infos(request)
    UploadFormSet = formset_factory(UploadFileForm, extra=5)
    if request.method == 'POST':
        formset = UploadFormSet(request.POST, request.FILES)
        replays = []
        if formset.is_valid():
            for form in formset:
                if form.cleaned_data:
                    logger.info("upload by request.user='%s'", request.user)
                    logger.info("form.cleaned_data=%s", form.cleaned_data)
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
                        logger.warn("written_bytes=%r != ufile.size=%r", written_bytes, ufile.size)
                        #return HttpResponse("Could not store the replay file. Please contact the administrator.")

                    timer.start("Parse_demo_file()")
                    demofile = parse_demo_file.Parse_demo_file(path)
                    timer.stop("Parse_demo_file()")
                    try:
                        demofile.check_magic()
                    except parse_demo_file.BadFileType:
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
                            UploadTmp.objects.filter(replay=replay).delete()
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

                        if not settings.DEBUG:
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
