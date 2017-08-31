# This file is part of the "spring relay site / srs" program. It is published
# under the GPLv3.
#
# Copyright (C) 2016 Daniel Troeder (daniel #at# admin-box #dot# com)
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import magic
import logging
import os

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.forms.formsets import formset_factory

from srs.upload import save_uploaded_file, parse_uploaded_file, AlreadyExistsError
from srs.models import ExtraReplayMedia, Replay, SrsTiming, get_owner_list
from srs.common import all_page_infos
from srs.forms import UploadFileForm, UploadMediaForm
import srs.parse_demo_file as parse_demo_file

logger = logging.getLogger("srs.views")

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
                    logger.info("upload by request.user=%r form.cleaned_data=%r", request.user, form.cleaned_data)
                    ufile = form.cleaned_data['file']
                    short = form.cleaned_data['short']
                    long_text = form.cleaned_data['long_text']
                    tags = form.cleaned_data['tags']
                    timer = SrsTiming()
                    timer.start("upload()")
                    (path, written_bytes) = save_uploaded_file(ufile.read(), ufile.name)
                    logger.info("User '%s' uploaded file '%s' with title '%s', parsing it now.", request.user,
                                os.path.basename(path), short[:20])
                    if written_bytes != ufile.size:
                        logger.warn("written_bytes=%r != ufile.size=%r", written_bytes, ufile.size)
                    try:
                        replay, msg = parse_uploaded_file(path, timer, tags, short, long_text, request.user)
                        logger.debug("replay=%r msg=%r", replay, msg)
                        replays.append((True, replay))
                    except parse_demo_file.BadFileType:
                        form._errors = {'file': [u'Not a spring demofile: %s.' % ufile.name]}
                        replays.append((False, 'Not a spring demofile: %s.' % ufile.name))
                        continue
                    except AlreadyExistsError as exc:
                        form._errors = {'file': [u'Uploaded replay already exists: "{}"'.format(exc.replay.title)]}
                        replays.append((False, 'Uploaded replay already exists: <a href="{}">{}</a>.'.format(
                            exc.replay.get_absolute_url(), exc.replay.title)))
                        continue
                    except Exception as exc:
                        form._errors = {'file': [u'Server error: {}'.format(exc)]}
                        replays.append((False, 'Server error. Please contact admin.'))
                        continue
                    finally:
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
            return render(request, 'multi_upload_success.html', c)
    else:
        # form = UploadFileForm()
        formset = UploadFormSet()
    c['formset'] = formset
    return render(request, 'upload.html', c)


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
                    comment = form.cleaned_data['comment']
                    if media:
                        media.seek(0)
                        media_magic_text = magic.from_buffer(media.read(1024))
                        media.seek(0)
                        media_magic_mime = magic.from_buffer(media.read(1024), mime=True)
                        media.seek(0)
                    else:
                        media_magic_text = None
                        media_magic_mime = None
                    erm = ExtraReplayMedia.objects.create(replay=replay, uploader=request.user, comment=comment,
                                                          media=media, image=image, media_magic_text=media_magic_text,
                                                          media_magic_mime=media_magic_mime)
                    c["media_files"].append(erm)
                    logger.info("User '%s' uploaded for replay:'%s' media:'%s' img:'%s' with comment:'%s'.",
                                request.user, replay, erm.media, erm.image, erm.comment[:20])
            return render(request, 'upload_media_success.html', c)
        else:
            logger.error("formset.errors: %s", formset.errors)
            logger.error("request.FILES: %s", request.FILES)
            logger.error("request.POST: %s", request.POST)
    else:
        formset = UploadMediaFormSet()
    c["formset"] = formset
    return render(request, 'upload_media.html', c)
