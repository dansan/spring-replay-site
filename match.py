# -*- coding: utf-8 -*-

from db_entities import *
from datetime import datetime,timedelta
from ranking import *

def getSectionContect( string, name ):
	b = string.find('BEGIN'+name)
	e = string.find('END'+name)
	return string[b+len('BEGIN'+name)+1:e-1]

def keyValPair(line):
	key = line.split('=')[0]
	val = line.split('=')[1]
	return (key , val)

def find_key(dic, val):
	return [k for k, v in dic.iteritems() if v == val][0]

def parseSec( sec ):
	dic = dict()
	lines=sec.split('\n')
	for line in lines:
		if len(line) < 2:
			continue
		(key,val) = keyValPair(line)
		dic[key] = val
	return dic

class MatchToDbWrapper():

	def __init__( self, stdout, battlefounder, ladder_id ):
		self.springoutput 	= stdout
		self.battlefounder 	= battlefounder
		self.ladder_id		= ladder_id
		self.game_started	= False
		self.game_over		= -1

	def CommitMatch(self,db):
		self.ParseSpringOutput()
		ladder = db.GetLadder(self.ladder_id )
		session = db.sessionmaker()
		match = Match()
		match.date 	= datetime.now() 
		match.modname  = ''
		match.mapname = ''
		match.replay = ''
		match.duration = timedelta(days=666)
		match.ladder_id = ladder.id
		session.add( match )
		session.commit()
		#session.refresh()
		for key,val in self.options.iteritems():
			s = MatchSetting()
			s.key = key
			s.val = val
			s.match_id = match.id
			session.add( s )
			session.commit()
		for key,val in self.restr.iteritems():
			s = MatchSetting()
			s.key = key
			s.val = val
			s.match_id = match.id
			session.add( s )
			session.commit()
		self.CommitPlayerResults(session,match)
		session.close()
		GlobalRankingAlgoSelector.GetInstance( ladder.ranking_algo_id ).Update( ladder.id, self, db )

	def CommitPlayerResults(self,session,match):
		for name,result in self.players.iteritems():
			p = session.query( Player ).filter( Player.nick == name ).first()
			if not p:
				p = Player( name )
				session.add( p )
				session.commit()
			result.player_id = p.id
			result.match_id = match.id
			session.add( result )
			session.commit()

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

		for teamid,ally in self.allies.iteritems():
			name = find_key( self.teams, teamid )
			self.players[ name ].ally = ally

		for line in game_section.split('\n'):
			tokens = line.split()
			assert len(tokens) > 0
			if tokens[0] == 'CONNECTED':
				assert len(tokens) > 1
				self.players[tokens[1]].connected = True
			elif tokens[0] == 'DESYNC':
				assert len(tokens) > 2
				self.players[tokens[3]].desync = True
			elif tokens[0] == 'LEAVE':
				assert len(tokens) > 2
				self.players[tokens[2]].quit = tokens[1]
			elif tokens[0] == 'TEAMDIED':
				assert len(tokens) > 2
				for name,team_id in self.teams.iteritems():
					if team_id == tokens[2]:
						self.players[name].died = tokens[1]
			elif tokens[0] == 'DISCONNECT':
				assert len(tokens) > 2
				self.players[tokens[2]].disconnect = tokens[1]
			elif tokens[0] == 'GAMESTART':
				self.game_started = True
			elif tokens[0] == 'GAMEOVER':
				if not self.game_started:
					print 'big bad error'
				else:
					assert len(tokens) > 1
					self.game_over = tokens[1]
					

