# This file is part of the "spring relay site / srs" program. It is published
# under the GPLv3.
#
# Copyright (C) 2012 Daniel Troeder (daniel #at# admin-box #dot# com)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

from django import forms
from ajax_select.fields import AutoCompleteSelectMultipleField
from srs.models import Player, PlayerAccount, Game, RatingBase
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

class AdvSearchForm(forms.Form):
    # don't forget to update search() and advsearch() if anything changes here
    text      = forms.CharField(widget=forms.TextInput(attrs={'size': '26'}), max_length=50, label="Description", required=False)
    comment   = forms.CharField(widget=forms.TextInput(attrs={'size': '26'}), max_length=50, label="Comment", required=False)
    tag       = AutoCompleteSelectMultipleField('tag', label="Tag", max_length=50, help_text=None, required=False, plugin_options = {'minLength': 2})
    player    = AutoCompleteSelectMultipleField('player', label="Player", max_length=50, help_text=None, required=False, plugin_options = {'minLength': 3})
    spectator = forms.BooleanField(label="Include spectators?", required=False)
    maps      = AutoCompleteSelectMultipleField('map', label="Map", max_length=50, help_text=None, required=False, plugin_options = {'minLength': 2})
    game      = AutoCompleteSelectMultipleField('game', label="Game", max_length=50, help_text=None, required=False)
    matchdate = forms.DateField(widget=forms.DateInput(attrs={'size': '26', 'class':'datePicker'}, format='%Y-%m-%d'), label="Day of match", required=False)
    uploaddate= forms.DateField(widget=forms.DateInput(attrs={'size': '26', 'class':'datePicker'}, format='%Y-%m-%d'), label="Day of upload", required=False)
    uploader  = AutoCompleteSelectMultipleField('user', label="Uploader", max_length=50, help_text=None, required=False)
    autohost  = AutoCompleteSelectMultipleField('autohostname', label="Autohost", max_length=50, help_text=None, required=False, plugin_options = {'minLength': 3})

    def __init__(self, *args, **kwargs):
        super(AdvSearchForm, self).__init__(*args, **kwargs)
        for field in ["game", "tag", "maps", "player", "uploader", "autohost"]:
            self.fields[field].widget.attrs['size'] = 26
            self.fields[field].widget.attrs['title'] = "Start typing. Click autocompleted results to add them to the query, use trashcan to remove it."

class ManualRatingAdjustmentForm(forms.Form):
    player     = forms.ChoiceField(widget=forms.Select(attrs={"onchange": "Dajaxice.srs.views.mra_update_game(Dajax.process, {'paid':this.value})"}))
    game       = forms.ChoiceField(widget=forms.Select(attrs={"onchange": "Dajaxice.srs.views.mra_update_match_type(Dajax.process, {'gameid':this.value, 'paid':$('#id_player').children('option:selected').val()})"}))
    match_type = forms.ChoiceField(widget=forms.Select(attrs={"onchange": "Dajaxice.srs.views.mra_update_ratings(Dajax.process, {'matchtype': this.value, 'gameid':$('#id_game').children('option:selected').val(), 'paid':$('#id_player').children('option:selected').val()})"}))
    elo        = forms.FloatField(min_value=0, max_value=2600, required=False)
    glicko     = forms.FloatField(min_value=0, max_value=2600, required=False)
    trueskill  = forms.FloatField(min_value=0, max_value=50, required=False)

    def __init__(self, *args, **kwargs):
        super(ManualRatingAdjustmentForm, self).__init__(*args, **kwargs)
        players = Player.objects.exclude(name__startswith="Bot (of").values_list("account", "name").distinct().order_by("name")
        self.fields["player"].choices = [(pa_id, name.ljust(30, ".")+" (%d, %s)"%(pa_id, PlayerAccount.objects.get(id=pa_id).preffered_name)) for (pa_id, name) in players if pa_id > 0]
        self.fields["player"].choices.insert(0, (0, "Please select a player."))

        self.fields["game"].choices = Game.objects.values_list("id", "name").order_by("name")
        self.fields["game"].choices.insert(0, (0, "Please select a game."))

        self.fields["match_type"].choices = RatingBase.MATCH_TYPE_CHOICES
        self.fields["match_type"].choices.insert(0, (0, "Please select a match type."))

class UnifyAccountsForm(forms.Form):
    player1 = forms.ChoiceField()
    player2 = forms.ChoiceField()

    def __init__(self, *args, **kwargs):
        super(UnifyAccountsForm, self).__init__(*args, **kwargs)
        playeraccounts = PlayerAccount.objects.exclude(accountid=0)#.values_list("accountid", "preffered_name", "primary_account")
        choices = list()
        for pa in playeraccounts: # (pa_id, name, pri_acc)
            if pa.primary_account:
                choices.append((pa.get_primary_account().accountid, "%06d"%pa.accountid+"..."+pa.preffered_name.ljust(30, ".")+" (%d, %s)"%(pa.get_primary_account().accountid, pa.get_primary_account().preffered_name)))
            else:
                choices.append((pa.accountid, "%06d"%pa.accountid+"..."+pa.preffered_name))
        choices.insert(0, (0, "Please select a player."))

        self.fields["player1"].choices = choices
        self.fields["player2"].choices = choices

    def clean(self):
        try:
            player1 = PlayerAccount.objects.get(accountid=self.cleaned_data.get("player1"))
            player2 = PlayerAccount.objects.get(accountid=self.cleaned_data.get("player2"))
        except Exception, e:
            logger.error("Invalid AccountIDs: player1='%s', player2='%s', Exeption='%s'", self.cleaned_data.get("player1"), self.cleaned_data.get("player2"), e)
            raise forms.ValidationError("Invalid AccountIDs")

        if player1 in player2.get_all_accounts():
            logger.error("Accounts are already unified: %s AND %s", player1, player2)
            raise forms.ValidationError("Accounts are already unified.")
        else:
            return self.cleaned_data
