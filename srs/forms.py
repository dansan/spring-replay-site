# This file is part of the "spring relay site / srs" program. It is published
# under the GPLv3.
#
# Copyright (C) 2016 Daniel Troeder (daniel #at# admin-box #dot# com)
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django import forms
from django.utils.safestring import mark_safe
from django.utils.encoding import force_unicode

from srs.models import Game

import logging

logger = logging.getLogger("srs.views")


class UploadFileForm(forms.Form):
    file = forms.FileField()
    short = forms.CharField(widget=forms.TextInput(attrs={'size': '53'}), max_length=50,
                            label="Short subject (50 char max)", required=False)
    long_text = forms.CharField(widget=forms.Textarea(attrs={'rows': '4', 'cols': '60'}), max_length=512,
                                label="Comment (512 char max)", required=False)
    tags = forms.CharField(widget=forms.TextInput(attrs={'size': '53'}), label="Tags (comma separated)", required=False)


class UploadMediaForm(forms.Form):
    media_file = forms.FileField(required=False)
    image_file = forms.ImageField(required=False)
    comment = forms.CharField(widget=forms.Textarea(attrs={'rows': '4', 'cols': '60'}), max_length=512,
                              label="Comment (512 char max)", required=False)


class EditReplayForm(forms.Form):
    short = forms.CharField(widget=forms.TextInput(attrs={'size': '53'}), max_length=50,
                            label="Short subject (50 char max)", required=False)
    long_text = forms.CharField(widget=forms.Textarea(attrs={'rows': '4', 'cols': '60'}), max_length=512,
                                label="Comment (512 char max)", required=False)
    tags = forms.CharField(widget=forms.TextInput(attrs={'size': '53'}), label="Tags (comma separated)", required=False)


class SLDBPrivacyForm(forms.Form):
    MODE_CHOICES = ((0,
                     '<p><b>Privacy disabled</b>:<br>Your exact trueskill rating is shown to<br>everyone on the replay website and in<br>"!status" output on the autohosts.</p>'),
                    (1,
                     '<b>Basic privacy enabled <u>(default)</u></b>:<br>Players and website visitors only see a<br>rough estimate of your trueskill rating.<br>If you log into the website you will still<br>see your own exact ratings. On the autohosts<br>only privileged users can still see an exact value<br>in "!status" output.'),
                    (2,
                     '<b>Full privacy enabled</b>:<br>Same as "Basic privacy", but even<br>privileged autohost users see only a rough<br>estimate in "!status" output.'))
    mode = forms.ChoiceField(required=False, label="", choices=MODE_CHOICES, widget=forms.RadioSelect())


def _game_choices():
    game_choices = list(Game.objects.all().order_by("name").values_list("id", "name"))
    game_choices.insert(0, (0, "No filter"))
    return game_choices


class GamePref(forms.Form):
    auto = forms.BooleanField(required=False, label="Restore previous state (default)",
                              widget=forms.CheckboxInput(attrs={"onclick": "toggle_game_choice(this)"}))
    game_choice = forms.ChoiceField(required=False, choices=_game_choices,
                                    widget=forms.Select(attrs={"class": "form-control"}))
