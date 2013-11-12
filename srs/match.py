# -*- coding: utf-8 -*-

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

import demoparser
from script import Script

import struct
import logging
logger = logging.getLogger(__package__)


class MyObj(object):
	def __init__(self, demofile):
		self.replay = demofile

	def list_players(self):
		for p,v in self.players.items():
			print "%s : %s"%(p, v.__dict__)

	def list_specs(self):
		for p,v in self.spectators.items():
			print "%s : %s"%(p, v.__dict__)

def ParseSpringOutput(self):
	def _save_playerinfo(playername, key, value):
		if playername in self.players:
			setattr(self.players[playername], key, value)
		else:
			setattr(self.spectators[playername], key, value)

	def _invalidPlayer(name):
		return name not in self.spectators and name not in self.players

	with open(self.replay, 'rb') as demofile:
		self.parser = demoparser.DemoParser(demofile)
		self.parser.check_magic()
		self.parser.parse_script()
		script_str = self.parser.getScript()
		open('/tmp/sc.txt', 'w').write(script_str)
		self.script = Script()
		self.script.parse(script_str)
		self.players = self.script.players
		self.players_script = self.script.players_script
		self.spectators = self.script.spectators
		self.bots = self.script.bots
		self.teams = self.script.teams
		self.allies = self.script.allies
		self.options = dict(self.script.modoptions.items()
						+ self.script.other.items() + self.script.mapoptions.items())
		self.restrictions = self.script.restrictions
		self.gameid = 'no game id found'
		packet = True
		currentFrame = 0
		playerIDToName = {}
		kop = open('/tmp/msg.data','w')
		while packet:
			packet = self.parser.readPacket()
			try:
				messageData = demoparser.parsePacket(packet)
				kop.write(str(messageData))
				kop.write('\n')
				def clean(name):
					return name.replace('\x00','')
				if messageData:
					try:
						clean_name = clean(messageData['playerName'])
					except:
						pass
					if messageData['cmd'] == 'keyframe':
						currentFrame = messageData['framenum']
					elif messageData['cmd'] == 'setplayername':
						if _invalidPlayer(clean_name):
							continue
						playerIDToName[messageData['playerNum']] = clean_name
						_save_playerinfo(clean_name, "connected", True)
					elif messageData['cmd'] == 'startplaying' and messageData['countdown'] == 0:
						self.game_started = True
					elif messageData['cmd'] == 'gameover':
						if not self.game_started:
							logger.error( 'game not started on gameover found', 'Match.py' )
						else:
							self.game_over = currentFrame
					elif messageData['cmd'] == 'gameid':
						self.gameid = messageData['gameID']
					elif messageData['cmd'] == 'playerleft':
						playername = clean(messageData['playerName'])
						if _invalidPlayer(clean_name):
							continue
						if messageData['bIntended'] == 0:
							_save_playerinfo(playername, "timeout", True)
						if messageData['bIntended'] == 1:
							_save_playerinfo(playername, "quit", True)
						if messageData['bIntended'] == 2:
							_save_playerinfo(playername, "kicked", True)
					elif messageData['cmd'] == 'team':
						if clean_name in self.script.spectators.keys():
							continue
						if messageData['action'] == 'team_died': #team died event
							deadTeam = messageData['param']
							for name,rank in self.players.iteritems():
								if rank.team == deadTeam:
									self.players[name].died = currentFrame
						elif messageData['action'] == 'giveaway': 
							#giving everything away == death 
							self.players[clean_name].died = currentFrame
					elif messageData["cmd"] == "startpos":
						if messageData["ready"] == 1:
							playername = clean(messageData['playerName'])
							if _invalidPlayer(playername):
								continue
							self.players[playername].start_pos_x = messageData["x"]
							self.players[playername].start_pos_y = messageData["y"]
							self.players[playername].start_pos_z = messageData["z"]
					elif messageData["cmd"] == "luamsg":
						if struct.unpack("<B", messageData["msg"][0])[0] == 138:
							# faction change
							playername = clean(messageData['playerName'])
							if _invalidPlayer(playername):
								continue
							faction = struct.unpack("<%iB"%(len(messageData["msg"][1:])), messageData["msg"][1:])
							logger.debug("%s changed faction to '%s'", playername, faction)
			except Exception, e:
				logger.error("Exception parsing packet '%s': %s", packet, e)
				raise e

		kop.close()
