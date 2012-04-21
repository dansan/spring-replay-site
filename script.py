import io
from ConfigParser import RawConfigParser as CfgParser
from collections import defaultdict

from db_entities import Result

class ScriptPlayer(object):
	def __init__(self,config,section):
		self.num = int(section[6:])
		self.name = config.get(section, 'Name')
		self.rank = int(config.get(section, 'Rank'))
		try:
			self.team = int(config.get(section, 'Team'))
			self.spectator = False
		except:
			self.spectator = True
		self.ally = -1
		
	def result(self):
		r = Result()
		r.ally = self.ally
		r.team = self.team
		return r
	
	
class ScriptAI(object):
	def __init__(self,config,section):
		self.num = int(section[2:])
		self.team = config.get(section, 'Team')
		self.name = config.get(section, 'Name')
		self.shortname = config.get(section, 'ShortName')
		self.ally = -1


class ScriptAlly(object):		
	def __init__(self,config,section):
		self.num = int(section[8:])
		self.team = config.get(section, 'Team')
		self.name = config.get(section, 'Name')
		self.shortname = config.get(section, 'ShortName')
		self.ally = -1
		
		
class ScriptTeam(object):		
	def __init__(self,config,section):
		self.num = int(section[4:])
		self.leader = config.get(section, 'TeamLeader')
		self.side = config.get(section, 'Side')
		self.shortname = config.get(section, 'ShortName')
		self.ally = config.get(section, 'AllyTeam')
		
		
class Script(object):
	def __init__(self,script):
		config = CfgParser({'team':-1})
		script = script.replace('}','').replace('{','').replace(';','')
		config.readfp(io.BytesIO(script))
		self.restrictions = dict()
		self.mapoptions = dict() 
		self.modoptions = dict()
		self.players = defaultdict(Result) 
		self.bots = dict()
		self.spectators = dict()
		self.teams = [] 
		self.allies = []
		self.other = dict()
		for section in config.sections():
			if section.startswith('player'):
				player = ScriptPlayer(config,section)
				if player.spectator:
					self.spectators[player.name] = player.result()
				else:
					self.players[player.name] = player.result()
			elif section.startswith('AI'):
				bot = ScriptAI(config,section)
				self.bots[bot.name] = bot
			elif section.startswith('ALLYTEAM'):
				self.allies.append(ScriptAlly(config,section))
			elif section.startswith('TEAM'):
				self.teams.append(ScriptTeam(config,section))
			elif section == 'restrict':
				self.restrictions = dict(config.items(section))
			elif section == 'mapoptions':
				self.mapoptions = dict(config.items(section))
			elif section == 'modoptions':
				self.modoptions = dict(config.items(section))
			if config.has_option(section, 'mapname'):
				self.other['mapname'] = config.get(section, 'mapname')
			if config.has_option(section, 'gametype'):
				self.other['modname'] = config.get(section, 'gametype')
				
