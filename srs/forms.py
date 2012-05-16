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
