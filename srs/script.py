# This file is part of the "spring relay site / srs" program. It is published
# under the GPLv3.
#
# Copyright (C) 2016-2020 Daniel Troeder (daniel #at# admin-box #dot# com)
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

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
from typing import Union
from collections import defaultdict


class Result():
    def __init__(self):
        self.team = -1
        self.disconnect = -1
        self.ally = -1
        self.died = -1
        self.desync = -1
        self.timeout = False
        self.connected = False
        self.quit = False
        self.kicked = False
        self.startposx = -1
        self.startposy = -1
        self.startposz = -1

    def __cmp__(self, other):
        assert isinstance(other, Result)
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

    def __repr__(self):
        try:
            return 'Result(player={} team={} died={} quit={})'.format(self.player.nick, self.team, self.died, self.quit)
        except:
            import logging
            logger = logging.getLogger(__name__)
            logger.exception("FIXME: to broad exception handling.")
            return 'Result(team={} died={} quit={})'.format(self.team, self.died, self.quit)


def try_make_numeric(val: str) -> Union[int, float, str]:
    if val.isdigit():
        return int(val)
    else:
        try:
            return float(val)
        except ValueError:
            pass
    return val


class ScriptObject(object):
    req_keys = []

    def __init__(self, section, data):
        if isinstance(section, bytes):
            section = section.decode("utf-8")
        if isinstance(data, bytes):
            data = data.decode("utf-8")
        if section not in ["mapoptions", "modoptions", "restrict", "game_setup_host"]:
            _i = 0
            while not section[_i].isdigit():
                _i += 1
            self.num = int(section[_i:])

        kvs = re.findall('(?P<key>.*?)=(?P<value>.*?);', data.strip(), re.DOTALL)
        for key, value in kvs:
            setattr(self, key, try_make_numeric(value))

        if self.req_keys and not any([hasattr(self, key) for key in self.req_keys]):
            raise Exception("Missing required key in section '%s'." % section)

    def __repr__(self):
            return "{}({})".format(self.__class__.__name__, self.__dict__)


class ScriptPlayer(ScriptObject):
    req_keys = ["spectator"]

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
            print("Missing required key 'lobbyid' or 'accountid' in section '%s': '%s'. Single Player match?" % (
                section, data))
            self.accountid = None

        if hasattr(self, "rank"):
            pass
        elif hasattr(self, "lobbyrank"):
            # demofile from zero-k
            self.rank = self.lobbyrank
        else:
            print("Missing required key 'rank' or 'lobbyrank' in section '%s': '%s'." % (section, data))
            self.rank = None

        if hasattr(self, "countrycode"):
            pass
        else:
            print("Missing required key 'countrycode' in section '%s': '%s'." % (section, data))
            self.countrycode = None

    def __repr__(self):
        if hasattr(self, "name"):
            return "ScriptPlayer({}, {})".format(getattr(self, "name", "-"), getattr(self, "accountid", "-"))
        else:
            return super(self, self.__repr__)


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
