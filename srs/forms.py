# This file is part of the "spring relay site / srs" program. It is published
# under the GPLv3.
#
# Copyright (C) 2012 Daniel Troeder (daniel #at# admin-box #dot# com)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django import forms
from django.utils.safestring import mark_safe
from django.utils.encoding import force_unicode

from srs.models import Game

import logging
logger = logging.getLogger(__package__)

class UploadFileForm(forms.Form):
    file      = forms.FileField()
    short     = forms.CharField(widget=forms.TextInput(attrs={'size': '53'}), max_length=50, label="Short subject (50 char max)", required=False)
    long_text = forms.CharField(widget=forms.Textarea(attrs={'rows':'4',  'cols': '60'}), max_length=512, label="Comment (512 char max)", required=False)
    tags      = forms.CharField(widget=forms.TextInput(attrs={'size': '53'}), label="Tags (comma separated)", required=False)

class UploadMediaForm(forms.Form):
    media_file = forms.FileField(required=False)
    image_file = forms.ImageField(required=False)
    comment    = forms.CharField(widget=forms.Textarea(attrs={'rows':'4',  'cols': '60'}), max_length=512, label="Comment (512 char max)", required=False)

class EditReplayForm(forms.Form):
    short     = forms.CharField(widget=forms.TextInput(attrs={'size': '53'}), max_length=50, label="Short subject (50 char max)", required=False)
    long_text = forms.CharField(widget=forms.Textarea(attrs={'rows':'4',  'cols': '60'}), max_length=512, label="Comment (512 char max)", required=False)
    tags      = forms.CharField(widget=forms.TextInput(attrs={'size': '53'}), label="Tags (comma separated)", required=False)

class RadioSelectTableRenderer(forms.widgets.RadioFieldRenderer):
    def render(self):
        return mark_safe(u'\n'.join([u'<tr><td>%s</td></tr>' % force_unicode(w) for w in self]))

class SLDBPrivacyForm(forms.Form):
    MODE_CHOICES = ((0, '<b>Privacy disabled</b>: your exact trueskill rating is shown to everyone on the replay website and in "!status" output on the autohosts.'),
                    (1, '<b>Basic privacy enabled <u>(default)</u></b>: players and website visitors only see a rough estimate of your trueskill rating. If you log into the website you will still see your own exact ratings. On the autohosts only privileged users can still see an exact value in !status output.'),
                    (2, '<b>Full privacy enabled</b>: same as "Basic privacy", but even privileged autohost users see only a rough estimate in !status output.'))
    mode = forms.ChoiceField(required=False, label="", choices=MODE_CHOICES, widget=forms.RadioSelect(renderer=RadioSelectTableRenderer))

class GamePref(forms.Form):
    GAME_CHOICES = list(Game.objects.all().order_by("name").values_list("id", "name"))
    GAME_CHOICES.insert(0, (0, "No filter"))
    auto         = forms.BooleanField(required=False, label="Restore previous state (default)", widget=forms.CheckboxInput(attrs={"onclick": "toggle_game_choice(this)"}))
    game_choice  = forms.ChoiceField(required=False, choices=GAME_CHOICES, widget=forms.Select(attrs={"class": "form-control"}))
