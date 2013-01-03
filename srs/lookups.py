# This file is part of the "spring relay site / srs" program. It is published
# under the GPLv3.
#
# Copyright (C) 2012 Daniel Troeder (daniel #at# admin-box #dot# com)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

import settings
from django.utils.html import escape

from ajax_select import LookupChannel

from django.contrib.auth.models import User
from models import Game, Map, PlayerAccount, Tag

class PublicLookupChannel(LookupChannel):
    def check_auth(self, request):
        return True

class GameLookup(PublicLookupChannel):
    model = Game

    def get_query(self, q, request):
        return Game.objects.filter(name__icontains=q).only("name").order_by('name')

    def get_result(self, obj):
        u""" result is the simple text that is the completion of what the person typed """
        return obj.name

    def format_match(self, obj):
        """ (HTML) formatted item for display in the dropdown """
#        return self.format_item_display(obj)
        return obj.name

    def format_item_display(self, obj):
        """ (HTML) formatted item for displaying item in the selected deck area """
        return u'<a href="%s" target="_blank">%s</a>' % (obj.get_absolute_url(), obj.name) 

class MapLookup(PublicLookupChannel):
    model = Map

    def get_query(self, q, request):
        return Map.objects.filter(name__icontains=q).only("name").order_by('name')

    def get_result(self, obj):
        return obj.name

    def format_match(self, obj):
        return u'%s<div><img src="%s"/></div>' % (obj.name, settings.STATIC_URL+'maps/'+obj.name+"_home.jpg")

    def format_item_display(self, obj):
        return u'<a href="%s" target="_blank">%s</a><div><img src="%s"/></div>' % (obj.get_absolute_url(), obj.name, settings.STATIC_URL+'maps/'+obj.name+"_home.jpg") 

class PlayerLookup(PublicLookupChannel):
    model = PlayerAccount

    def get_query(self, q, request):
        return PlayerAccount.objects.exclude(accountid=0).filter(player__name__icontains=q).distinct().select_related("player").order_by('player__name')

    def get_result(self, obj):
        return reduce(lambda x, y: x+" "+y, obj.get_names()).rstrip()

    def format_match(self, obj):
        return u'%s' % reduce(lambda x, y: x+" "+y, obj.get_names()).rstrip()

    def format_item_display(self, obj):
        return u'<a href="%s" target="_blank">%s</a>' % (obj.get_absolute_url(), reduce(lambda x, y: x+" "+y, obj.get_names()).rstrip())

class TagLookup(PublicLookupChannel):
    model = Tag

    def get_query(self, q, request):
        return Tag.objects.filter(name__icontains=q).order_by('name')

    def get_result(self, obj):
        return obj.name

    def format_match(self, obj):
        return obj.name

    def format_item_display(self, obj):
        return u'<a href="%s" target="_blank">%s</a>' % (obj.get_absolute_url(), obj.name)

class UserLookup(PublicLookupChannel):
    model = User

    def get_query(self, q, request):
        return User.objects.filter(username__icontains=q).only("username").order_by('username')

    def get_result(self, obj):
        return obj.username

    def format_match(self, obj):
        return u'%s' % obj.username

    def format_item_display(self, obj):
        return u'<a href="%s" target="_blank">%s</a>' % (obj.get_absolute_url(), obj.username)
