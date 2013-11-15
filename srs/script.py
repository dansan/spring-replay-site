# This file is part of the "spring relay site / srs" program. It is published
# under the GPLv3.
#
# Copyright (C) 2013 Daniel Troeder (daniel #at# admin-box #dot# com)
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <http://www.gnu.org/licenses/>.

#
# The code in this file was originally part of the SpringLadder project
# (https://github.com/renemilk/SpringLadder) by koshi/renemilk and
# BrainDamage. SpringLadder is licensed as "Do What The Fuck You Want To
# Public License, Version 2".
#
# Future modifications of the code as part of the "spring relay site" project
# are licensed as GPLv3 (see above).
#

import re
from collections import defaultdict

class Result():

    def __init__(self):
        self.team         = -1
        self.disconnect = -1
        self.ally        = -1
        self.died        = -1
        self.desync        = -1
        self.timeout    = False
        self.connected    = False
        self.quit        = False
        self.kicked        = False
        self.startposx = -1
        self.startposy = -1
        self.startposz = -1

    def __cmp__(self,other):
        assert isinstance(other,Result)
        valuetocompare1 = -1
        valuetocompare2 = -1
        if self.disconnect < self.match.last_frame and self.quit:
            valuetocompare1 = self.disconnect
        if other.disconnect < self.match.last_frame and other.quit:
            valuetocompare2 = other.disconnect
        if self.quit != -1 and self.quit < self.match.last_frame:
            valuetocompare1 = self.quit
        if other.quit != -1 and other.quit < self.match.last_frame:
            valuetocompare2 = other.quit
        if other.kicked or self.kicked:
            return 0
        return valuetocompare1 < valuetocompare2

    def __str__(self):
        try:
            return 'Result: %s team(%d) died(%d) quit(%d) '%(self.player.nick,
                        self.team,self.died,self.quit)
        except:
            return'Result: team(%s) died(%d) quit(%d) '%(
                self.team,self.died,self.quit)

def try_make_numeric(val):
    if val.isdigit():
        return int(val)
    else:
        try:
            return float(val)
        except Exception:
            pass
    return val

class ScriptObject(object):

    def __init__(self, section, data):
        if not section in ["mapoptions", "modoptions", "restrict", "game_setup_host"]:
            _i = 0
            while not section[_i].isdigit():
                _i += 1
            self.num = int(section[_i:])

        kvs = re.findall('(?P<key>.*?)=(?P<value>.*?);', data.strip(), re.DOTALL)
        for key, value in kvs:
            setattr(self, key, try_make_numeric(value))

        if self.req_keys and not any([hasattr(self, key) for key in self.req_keys]):
            raise Exception("Missing required key in section '%s'."%section)

class ScriptPlayer(ScriptObject):
    req_keys = ["countrycode", "spectator"]

    def __init__(self, section, data):
        self.team = None
        self.ally = -1

        super(ScriptPlayer, self).__init__(section, data)

        if hasattr(self, "accountid"):
            pass
        elif hasattr(self, "lobbyid"):
            # demofile from zero-k
            self.accountid = self.lobbyid
        else:
            print "Missing required key 'lobbyid' or 'accountid' in section '%s': '%s'. Single Player match?"%(section, data)
            self.accountid = None

        if hasattr(self, "rank"):
            pass
        elif hasattr(self, "lobbyrank"):
            # demofile from zero-k
            self.accountid = self.lobbyrank
        else:
            raise Exception("Missing required key 'rank' or 'lobbyrank' in section '%s': '%s'."%(section, data))

#     def result(self):
#         r = Result()
#         r.ally = self.ally
#         r.team = self.team
#         #if r.team < 0:
#         #    raise Exception('djiepo')
#         for key, value in self.__dict__.items():
#             if not key == "result":
#                 setattr(r, key, value)
#         return r

class ScriptAI(ScriptObject):
    req_keys = ["host", "shortname"]

class ScriptAlly(ScriptObject):
    req_keys = ["numallies"]

class ScriptTeam(ScriptObject):
    req_keys = ["allyteam", "handicap", "rgbcolor", "side", "teamleader"]

class ScriptRestrictions(ScriptObject):
    req_keys = []

class ScriptMapoptions(ScriptObject):
    req_keys = []

class ScriptModoptions(ScriptObject):
    req_keys = []

class ScriptGamesetup(ScriptObject):
    req_keys = []

class Script(object):
    def __init__(self):
        self.restrictions = dict()
        self.mapoptions = dict()
        self.modoptions = dict()
        self.players = defaultdict(Result)
        self.bots = dict()
        self.spectators = defaultdict(Result)
        self.teams = list()
        self.allies = list()
        self.other = dict()
