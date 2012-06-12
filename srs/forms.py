# This file is part of the "spring relay site / srs" program. It is published
# under the GPLv3.
#
# Copyright (C) 2012 Daniel Troeder (daniel #at# admin-box #dot# com)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django import forms

class UploadFileForm(forms.Form):
    file      = forms.FileField()
    short     = forms.CharField(widget=forms.TextInput(attrs={'size': '53'}), max_length=50, label="Short subject (50 char max)", required=False)
    long_text = forms.CharField(widget=forms.Textarea(attrs={'rows':'4',  'cols': '60'}), max_length=512, label="Comment (512 char max)", required=False)
    tags      = forms.CharField(widget=forms.TextInput(attrs={'size': '53'}), label="Tags (comma separated)", required=False)

class EditReplayForm(forms.Form):
    short     = forms.CharField(widget=forms.TextInput(attrs={'size': '53'}), max_length=50, label="Short subject (50 char max)", required=False)
    long_text = forms.CharField(widget=forms.Textarea(attrs={'rows':'4',  'cols': '60'}), max_length=512, label="Comment (512 char max)", required=False)
    tags      = forms.CharField(widget=forms.TextInput(attrs={'size': '53'}), label="Tags (comma separated)", required=False)

class AdvSearchForm(forms.Form):
    # don't forget to update search() and advsearch() if anything changes here
    text      = forms.CharField(widget=forms.TextInput(attrs={'size': '20'}), max_length=50, label="Description", required=False)
    comment   = forms.CharField(widget=forms.TextInput(attrs={'size': '20'}), max_length=50, label="Comment", required=False)
    tag       = forms.CharField(widget=forms.TextInput(attrs={'size': '20'}), max_length=50, label="Tag", required=False)
    player    = forms.CharField(widget=forms.TextInput(attrs={'size': '20'}), max_length=50, label="Player", required=False)
    spectator = forms.BooleanField(label="Include spectators?", required=False)
    maps      = forms.CharField(widget=forms.TextInput(attrs={'size': '20'}), max_length=50, label="Map", required=False)
    game      = forms.CharField(widget=forms.TextInput(attrs={'size': '20'}), max_length=50, label="Game", required=False)
    matchdate = forms.DateField(widget=forms.DateInput(attrs={'class':'datePicker'}, format='%Y-%m-%d'), label="Day of match", required=False)
    uploaddate= forms.DateField(widget=forms.DateInput(attrs={'class':'datePicker'}, format='%Y-%m-%d'), label="Day of upload", required=False)
    uploader  = forms.CharField(widget=forms.TextInput(attrs={'size': '20'}), max_length=50, label="Uploader", required=False)
