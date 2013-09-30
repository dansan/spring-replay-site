import io
from ConfigParser import RawConfigParser as CfgParser
from collections import defaultdict
# import datetime

# from db_entities import Result
class Result():
# 	__tablename__ 	= 'results'
# 	id 				= Column( Integer, primary_key=True )
# 	player_id 		= Column( Integer, ForeignKey( Player.id ) )
# 	match_id 		= Column( Integer, ForeignKey( Match.id ) )
# 	ladder_id 		= Column( Integer, ForeignKey( Ladder.id ),index=True )
# 	date 			= datetime.datetime(1,1,1)
# 	team			= int()
# 	ally			= int()
# 	disconnect		= int()
# 	quit			= bool()
# 	died			= int()
# 	desync			= int()
# 	timeout			= bool()
# 	kicked			= bool()
# 	connected		= bool()

# 	player			= relation(Player)
# 	match			= relation(Match)

	def __init__(self):
		self.team 		= -1
		self.disconnect = -1
		self.ally		= -1
		self.died		= -1
		self.desync		= -1
		self.timeout	= False
		self.connected	= False
		self.quit		= False
		self.kicked		= False

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
			self.team = None
		self.ally = -1
		
	def result(self):
		r = Result()
		r.ally = self.ally
		r.team = self.team
		#if r.team < 0:
		#	raise Exception('djiepo')
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
		config = CfgParser({'team':None})
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
				
