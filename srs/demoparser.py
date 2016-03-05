# This file is part of the "spring relay site / srs" program. It is published
# under the GPLv3.
#
# Copyright (C) 2016 Daniel Troeder (daniel #at# admin-box #dot# com)
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

import struct
import zlib
import logging

logger = logging.getLogger("srs.upload")


class PlayerDict(dict):
    def __getitem__(self, item):
        return dict.__getitem__(self, item) if item in self else None


class Demoparser(object):
    def __init__(self):
        self.players = PlayerDict()

    def write(self, varis, *keys):
        #	blacklist = ('newframe', 'playerinfo', 'luamsg', 'mapdraw', 'aicommand', 'self.playerstat')
        blacklist = ('newframe', 'playerinfo', 'mapdraw', 'aicommand')
        returnval = dict()
        if varis['cmd'] in blacklist: return
        for key in keys:
            item = varis[key]
            returnval[key] = item
        return returnval

    def parsePacket(self, packet):
        if not packet or not packet['data']: return
        data = packet['data']

        cmd = ord(data[0])
        data = data[1:]
        if cmd == 1:
            cmd = 'keyframe'
            framenum = struct.unpack('<i', data)[0]
            return self.write(locals(), 'cmd', 'framenum')
        elif cmd == 2:
            cmd = 'newframe'
            return self.write(locals(), 'cmd')
        elif cmd == 3:
            cmd = 'quit'
            return self.write(locals(), 'cmd')
        elif cmd == 4:
            cmd = 'startplaying'
            countdown = struct.unpack('<I', data)[0]
            return self.write(locals(), 'cmd', 'countdown')
        elif cmd == 5:
            cmd = 'setplayernum'
            playerNum = ord(data)
            return self.write(locals(), 'cmd', 'playerNum')
        elif cmd == 6:
            cmd = 'setplayername'
            size, playerNum = struct.unpack('<BB', data[:2])
            playerName = data[2:]
            if not playerNum in self.players:
                self.players[playerNum] = playerName.strip('\0')
            return self.write(locals(), 'cmd', 'size', 'playerNum', 'playerName')
        elif cmd == 7:
            cmd = 'chat'
            size, fromID, toID = struct.unpack('<3B', data[:3])
            message = data[3:]
            playerName = self.players[fromID] or ''
            return self.write(locals(), 'cmd', 'size', 'fromID', 'playerName', 'toID', 'message')
        elif cmd == 8:
            cmd = 'randseed'
            randSeed = struct.unpack('<I', data)[0]
            return self.write(locals(), 'cmd', 'randSeed')
        elif cmd == 9:
            cmd = 'gameid'
            gameID = "%02x%02x%02x%02x%02x%02x%02x%02x%02x%02x%02x%02x%02x%02x%02x%02x" % struct.unpack("16B", data)
            return self.write(locals(), 'cmd', 'gameID')
        elif cmd == 10:
            cmd = "NETMSG_PATH_CHECKSUM"
            return self.write(locals(), "cmd")
        elif cmd == 11:
            cmd = 'command'
            size, playerNum, cmdID, options = struct.unpack('<hBiB', data[:8])
            params = struct.unpack('<%if' % ((len(data) - 6) / 4), data[8:])
            playerName = self.players[playerNum] or ''
            return self.write(locals(), 'cmd', 'size', 'playerNum', 'playerName', 'cmdID', 'options', 'params')
        elif cmd == 12:
            cmd = 'select'
            size, playerNum = struct.unpack('<hB', data[:3])
            selectedUnitIDs = struct.unpack('<%ih' % ((len(data) - 3) / 2), data[3:])
            playerName = self.players[playerNum] or ''
            return self.write(locals(), 'cmd', 'size', 'playerNum', 'playerName', 'selectedUnitIDs')
        elif cmd == 13:
            cmd = 'pause'
            playerNum, bPaused = struct.unpack('<BB', data)
            playerName = self.players[playerNum] or ''
            return self.write(locals(), 'cmd', 'playerNum', 'playerName', 'bPaused')
        elif cmd == 14:
            cmd = 'aicommand'
            size, playerNum, unitID, aiID, options = struct.unpack('<hBhiB', data[:10])
            # params = struct.unpack('<%if'%((len(data)-10)/4), data[10:])
            # playerName = self.players[playerNum] or ''
            return dict()
        # return self.write(locals(), 'cmd', 'size', 'playerNum', 'playerName', 'unitID', 'aiID', 'options', 'params')
        elif cmd == 15:
            return dict()
            cmd = 'aicommands'
            msgsize, playerNum, unitIDCount = struct.unpack('<hBh', data[:5])
            pos = (unitIDCount * 2) + 5
            d = data[5:pos]
            print 'pos %d data %s' % (pos, d)
            unitIDs = struct.unpack('<%dh' % (unitIDCount), data[5:pos])
            commandCount = struct.unpack('<h', data[pos:pos + 2])[0]
            pos += 2
            commands = []
            for i in xrange(commandCount):
                cmdID, options, size = struct.unpack('<iBh', data[pos:pos + 7])
                pos += 7
                params = struct.unpack('<%if' % size, data[pos:pos + (4 * size)])
                pos += 4 * size
                commands.append((cmdID, options, size, params))
            playerName = self.players[playerNum] or ''
            return self.write(locals(), 'cmd', 'msgsize', 'playerNum', 'playerName', 'unitIDCount', 'unitIDs',
                              'commands')
        elif cmd == 16:
            cmd = 'aishare'
            playerNum, sourceTeam, destTeam, metal, energy, unitIDCount = struct.unpack('<3Bffh', data[13:])
            unitIDs = struct.unpack('<%ih' % unitIDCount, data[:13])
            playerName = self.players[playerNum] or ''
            return self.write(locals(), 'cmd', 'playerNum', 'playerName', 'sourceTeam', 'destTeam', 'metal', 'energy',
                              'unitIDCount', 'unitIDs')
        elif cmd == 17:
            cmd = 'memdump'
            print 'OMG A MEMORY DUMP'
            return self.write(locals(), 'cmd')
        elif cmd == 19:
            cmd = 'user_speed'
            playerNum, userSpeed = struct.unpack('<Bf', data)
            playerName = self.players[playerNum] or ''
            return self.write(locals(), 'cmd', 'playerNum', 'playerName', 'userSpeed')
        elif cmd == 20:
            cmd = 'internal_speed'
            internalSpeed = struct.unpack('<f', data)[0]
            return self.write(locals(), 'cmd', 'internalSpeed')
        elif cmd == 21:
            cmd = 'cpu_usage'
            cpuUsage = struct.unpack('<f', data)[0]
            return self.write(locals(), 'cmd', 'cpuUsage')
        elif cmd == 22:
            cmd = 'direct_control'
            playerNum = ord(data)
            playerName = self.players[playerNum] or ''
            return self.write(locals(), 'cmd', 'playerNum', 'playerName')
        elif cmd == 23:
            cmd = 'dc_update'
            playerNum, status, heading, pitch = struct.unpack('<BBhh', data)
            playerName = self.players[playerNum] or ''
            return self.write(locals(), 'cmd', 'playerNum', 'playerName', 'status', 'heading', 'pitch')
        elif cmd == 25:
            cmd = 'attemptconnect'
            size = struct.unpack('<H', data[0])[0]
            name, password, version = data[1:].split('\0', 2)
            version = version.strip('\0')
            return self.write(locals(), 'cmd', 'size', 'name', 'password', 'version')
        elif cmd == 26:
            cmd = 'share'
            playerNum, shareTeam, shareUnits, shareMetal, shareEnergy = struct.unpack('<3Bff', data)
            playerName = self.players[playerNum] or ''
            return self.write(locals(), 'cmd', 'playerNum', 'playerName', 'shareTeam', 'shareUnits', 'shareMetal',
                              'shareEnergy')
        elif cmd == 27:
            cmd = 'setshare'
            playerNum, team, metalShareFraction, energyShareFraction = struct.unpack('<BBff', data)
            playerName = self.players[playerNum] or ''
            return self.write(locals(), 'cmd', 'playerNum', 'playerName', 'team', 'metalShareFraction',
                              'energyShareFraction')
        elif cmd == 28:
            cmd = 'sendself.playerstat'
            return self.write(locals(), 'cmd')
        elif cmd == 29:
            cmd = 'self.playerstat'  # fails
            # playerNum, wtf = struct.unpack()
            data = 'unparsed'
            return self.write(locals(), 'cmd', 'data')
        elif cmd == 30:
            cmd = 'gameover'
            return self.write(locals(), 'cmd')
        elif cmd == 31:  # okay, this fails on 0.80.x ... gotta check why.
            cmd = 'mapdraw'
            data = 'unparsed'
            return self.write(locals(), 'cmd', 'data')
            size, playerNum, command = struct.unpack('<3B', data[:3])
            data = data[3:]
            if command == 0:  # point = 0, erase = 1, line = 2
                x, z = struct.unpack('<hh', data[:4])
                label = data[4:]
            elif command == 1:
                x, z = struct.unpack('<hh', data)
            elif command == 2:
                x1, z1, x2, z2 = struct.unpack('<4hx', data)
        elif cmd == 33:
            cmd = 'syncresponse'
            playerNum, frameNum, checksum = struct.unpack('<BiI', data)
            playerName = self.players[playerNum] or ''
            return self.write(locals(), 'cmd', 'playerNum', 'playerName', 'frameNum', 'checksum')
        elif cmd == 35:
            cmd = 'systemmsg'
            size, playerNum = struct.unpack('<BB', data[:2])
            message = data[2:]
            playerName = self.players[playerNum] or ''
            return self.write(locals(), 'cmd', 'size', 'playerNum', 'playerName', 'message')
        elif cmd == 36:
            cmd = 'startpos'
            playerNum, team, ready, x, y, z = struct.unpack('<3B3f',
                                                            data)  # ready - 0 = not ready, 1 = ready, 2 = don't update readiness
            playerName = self.players[playerNum] or ''
            return self.write(locals(), 'cmd', 'playerNum', 'playerName', 'team', 'ready', 'x', 'y', 'z')
        elif cmd == 38:
            cmd = 'playerinfo'
            playerNum, cpuUsage, ping = struct.unpack('<BfI', data)  # ping is in number of frames
            playerName = self.players[playerNum] or ''
            return self.write(locals(), 'cmd', 'playerNum', 'playerName', 'cpuUsage', 'ping')
        elif cmd == 39:
            cmd = 'playerleft'
            playerNum, bIntended = struct.unpack('<BB', data)  # 0 = lost connection, 1 = left, 2 = forced (kicked)
            readableIntended = {0: 'lost connection', 1: 'left', 2: 'forced (kicked)'}[bIntended]
            playerName = self.players[playerNum] or ''
            return self.write(locals(), 'cmd', 'playerNum', 'playerName', 'bIntended', 'readableIntended')
        elif cmd == 41:
            cmd = "NETMSG_SD_CHKREQUEST"
            return self.write(locals(), "cmd")
        elif cmd == 42:
            cmd = "NETMSG_SD_CHKRESPONSE"
            return self.write(locals(), "cmd")
        elif cmd == 43:
            cmd = "NETMSG_SD_BLKREQUEST"
            return self.write(locals(), "cmd")
        elif cmd == 44:
            cmd = "NETMSG_SD_BLKRESPONSE"
            return self.write(locals(), "cmd")
        elif cmd == 45:
            cmd = "NETMSG_SD_RESET"
            return self.write(locals(), "cmd")
        elif cmd == 50:
            cmd = 'luamsg'
            size, playerNum, script, mode = struct.unpack('<HBHB', data[:6])
            msg = data[6:]
            playerName = self.players[playerNum] or ''
            (msgid,) = struct.unpack("<B", msg[0])
            return self.write(locals(), 'cmd', 'size', 'playerNum', 'playerName', 'script', 'mode', 'msg', 'msgid')
        elif cmd == 51:
            cmd = 'team'
            playerNum, action = struct.unpack('<BB', data[:2])
            param = None
            if action != 2: param = ord(data[2])

            if action == 1:
                action = 'giveaway'
            # param is the recipient team
            elif action == 2:
                action = 'resign'
            elif action == 3:
                action = 'join_team'
            # param is the team to join
            elif action == 4:
                action = 'team_died'
            # team which had died (sent by all self.players to prevent cheating)
            elif action == 5:
                action = 'ai_created'
            # team which is now controlled by a skirmish AI
            elif action == 6:
                action = 'ai_destroyed'
            # team which had its controlling skirmish AI be destroyed
            playerName = self.players[playerNum] or ''
            return self.write(locals(), 'cmd', 'playerNum', 'playerName', 'action', 'param')
        elif cmd == 52:
            cmd = 'gamedata'
            # f = open('gamedata.dat', 'wb')
            # f.return self.write(chr(52)+data)
            # f.close()
            size, compressedSize = struct.unpack('<HH', data[:4])
            setupText = zlib.decompress(data[4:compressedSize + 4])
            data = data[compressedSize + 4:]
            # print data
            # print __import__('binascii').hexlify(data)
            # return
            # mapName, modName, data = data.split('\0', 2)
            # print mapName, modName
            if len(data) == 12:  # 0.80 or later
                mapChecksum, modChecksum, randomSeed = struct.unpack('<3i', data)
                return self.write(locals(), 'cmd', 'size', 'compressedSize', 'setupText', 'mapChecksum', 'modChecksum',
                                  'randomSeed')
            elif False:
                print __import__('binascii').hexlify(data)
                script, mapName, modName, data = data.split('\0', 3)
                print script, mapName, modName
                print len(data)
                mapChecksum, modChecksum, randomSeed = struct.unpack('<3i', data)
                print mapChecksum, modChecksum, randomSeed
            # print size, compressedSize, setupText, mapChecksum, modChecksum, randomSeed
            else:
                data = 'unparsed, old replay format'
                return self.write(locals(), 'cmd', 'data')
        elif cmd == 53:
            cmd = 'alliance'
            playerNum, otherAllyTeam, allianceState = struct.unpack('<3B', data)  # 0 = not allied, 1 = allied
            readableAllianceState = {0: 'not allied', 1: 'allied'}[allianceState]
            playerName = self.players[playerNum] or ''
            return self.write(locals(), 'cmd', 'playerNum', 'playerName', 'otherAllyTeam', 'allianceState',
                              'readableAllianceState')
        elif cmd == 54:
            cmd = 'ccommand'
            size, playerNum = struct.unpack('<Hi', data[:6])
            command, extra = data[6:].split('\0', 1)
            playerName = self.players[playerNum] or ''
            return self.write(locals(), 'cmd', 'size', 'playerNum', 'playerName', 'command', 'extra')
        elif cmd == 60:
            cmd = 'teamstat'
            data = 'unparsed'
            return self.write(locals(), 'cmd', 'data')
        elif cmd == 65:
            cmd = "NETMSG_ATTEMPTCONNECT"
            return self.write(locals(), "cmd")
        elif cmd == 70:
            cmd = "NETMSG_AI_CREATED"
            return self.write(locals(), "cmd")
        elif cmd == 71:
            cmd = "NETMSG_AI_STATE_CHANGED"
            return self.write(locals(), "cmd")
        elif cmd == 72:
            cmd = "NETMSG_REQUEST_TEAMSTAT"
            return self.write(locals(), "cmd")
        elif cmd == 75:
            cmd = "NETMSG_CREATE_NEWPLAYER"
            return self.write(locals(), "cmd")
        elif cmd == 76:
            cmd = "NETMSG_AICOMMAND_TRACKED"
            return self.write(locals(), "cmd")
        elif cmd == 77:
            cmd = "NETMSG_GAME_FRAME_PROGRESS"
            return self.write(locals(), "cmd")
        else:
            logger.error("Unknown cmd found. packet: %s cmd: %s data: %s", packet, cmd, data)
