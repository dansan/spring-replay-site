# -*- coding: utf-8 -*-

from db_entities import *
from datetime import datetime
from ranking import *

def getSectionContect( string, name ):
	b = string.find('BEGIN'+name)
	e = string.find('END'+name)
	return string[nb:e]

def keyValPair(line):
	key = line.split('=')[0]
	val = line.split('=')[1]
	return (val , key)

def parseSec( sec )
	dic = dict()
	for line in sec:
		(key,val) = keyValPair(line)
		dic[key] = val
	return dic

class MatchToDbWrapper(Object):

	def __init__( self, stdout, battlefounder, ladder_id )
		self.springoutput 	= stdout
		self.battlefounder 	= battlefounder
		self.ladder_id		= ladder_id
		self.game_started	= False
		self.game_over		= -1

	def CommitMatch(self,db):
		session = db.sessionmaker()
		match = Match()
		match.date 	= datetime.now() 
		match.modname  = ''
		match.mapname = ''
		match.replay = ''
		match.duration = 1
		session.add( match )
		session.commit()
		session.refresh()
		for key,val in dict(self.options.items() + self.restr.items()):
			s = MatchSetting()
			s.key = key
			s.val = value
			s.match_id = match.id
			session.add( s )
			session.commit()
		self.CommitPlayerResults(session,match)
		GlobalRankingAlgoSelector.GetInstance( match.ranking_algo_id ).Update( match.ladder_id, self, db )

	def CommitPlayerResults(self,session,match):
		for name,result in self.players:
			p = session.query( Player ).filter( Player.nick == name ).first()
			result.player_id = p.id
			result.match_id = match.id
			session.add( r )
			session.commit()
		return results

	def ParseSpringOutput(self):
		setup_section 	= getSectionContect( self.springoutput, 'SETUP' )
		
		self.teams		= parseSec( getSectionContect( setup_section, 'TEAMS' 		) )
		self.allies		= parseSec( getSectionContect( setup_section, 'ALLYTEAMS' 	) )
		self.options 	= parseSec( getSectionContect( setup_section, 'OPTIONS' 	) )
		self.restr		= parseSec( getSectionContect( setup_section, 'RESTRICTIONS') )

		game_section 	= getSectionContect( self.springoutput, 'GAME' )
		num_players = len(self.teams)
		self.players = dict()
		
		for name,team in self.teams.iteritems():
			r = Result()
			r.team = team
			self.players[ name ] = r

		for line in game_section:
			tokens = line.split()
			assert len(tokens) > 0
			if token[0] == 'CONNECTED':
				assert len(tokens) > 1
				self.players[tokens[1]].connected = True
			elif token[0] == 'DESYNC':
				assert len(tokens) > 2
				self.players[tokens[3]].desync = True
			elif token[0] == 'LEAVE':
				assert len(tokens) > 2
				self.players[tokens[2]].quit = tokens[1]
			elif token[0] == 'TEAMDIED':
				assert len(tokens) > 2
				for name,team_id in self.teams.iteritems():
					if team_id == tokens[2]:
						self.players[name].died = tokens[1]
			elif token[0] == 'DISCONNECT':
				assert len(tokens) > 2
				self.players[tokens[2]].disconnect = tokens[1]
			elif token[0] == 'GAMESTART':
				self.game_started = True
			elif token[0] == 'GAMEOVER':
				if not self.game_started:
					print 'big bad error'
				else:
					assert len(tokens) > 1
					self.game_over = tokens[1]
					

