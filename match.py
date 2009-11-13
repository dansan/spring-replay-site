# -*- coding: utf-8 -*-

from db_entities import *
from datetime import datetime,timedelta
from ranking import *

class InvalidOptionSetup( Exception ):
	def __init__(self, gameid, ladderid):
		self.gameid = gameid
		self.ladderid = ladderid

	def __str__(self):
		return "Setup for game %s did not match ladder rules for ladder %d" %(self.gameid,self.ladderid)

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

	def CheckOptionOk( self, db, keyname, value ):
		if db.GetOptionKeyValueExists( self.ladder_id, False, keyname, value ): # option in the blacklist
			return False
		if db.GetOptionKeyExists( self.ladder_id, True, keyname ): # whitelist not empty
			return db.GetOptionKeyValueExists( self.ladder_id, True, keyname, value )
		else:
			return True

	def CheckValidOptionsSetup( self, db ):
		laddername = db.GetLadderName( self.ladder_id )
		for key in self.options:
			value = self.options[key]
			IsOk = self.CheckOptionOk( db, key, value )
			if not IsOk:
				return False
		return True

	def CheckValidSetup( self, db ):
		a = self.CheckvalidPlayerSetup(db)
		b = self.CheckValidOptionsSetup(db)
		return a and b

	def CheckvalidPlayerSetup( self, db ):
		laddername = db.GetLadderName( self.ladder_id )

		teamsdict = dict()
		alliesdict = dict()
		countedbots = []
		for player in self.teams:
			if not db.AccessCheck( self.ladder_id, player, Roles.User ):
				return False
			team = self.teams[player]
			if not team in teamsdict:
				teamsdict[team] = 1
			else:
				teamsdict[team] += 1
			if player in self.bots:
				libname = self.bots[player]
				if not libname in countedbots: # don't allow more than 1 bot of the same type
					countedbots.append(libname)
				else:
					return False
		for team in self.allies:
			ally = self.allies[team]
			if not ally in alliesdict:
				alliesdict[ally] = 1
			else:
				alliesdict[ally] += 1

		teamcount = len(teamsdict)
		allycount = len(alliesdict)
		aicount = len(self.bots)
		minaicount = db.GetLadderOption( self.ladder_id, "min_ai_count" )
		maxaicount = db.GetLadderOption( self.ladder_id, "max_ai_count" )
		minteamcount = db.GetLadderOption( self.ladder_id, "min_team_count" )
		maxteamcount = db.GetLadderOption( self.ladder_id, "max_team_count" )
		minallycount = db.GetLadderOption( self.ladder_id, "min_ally_count" )
		maxallycount = db.GetLadderOption( self.ladder_id, "max_ally_count" )
		if aicount < minaicount:
			return False
		if aicount > maxaicount:
			return False
		if teamcount < minteamcount:
			return False
		if teamcount > maxteamcount:
			return False
		if allycount < minallycount:
			return False
		if allycount > maxallycount:
			return False
		minteamsize = db.GetLadderOption( self.ladder_id, "min_team_size" )
		maxteamsize = db.GetLadderOption( self.ladder_id, "max_team_size" )
		minallysize = db.GetLadderOption( self.ladder_id, "min_ally_size" )
		maxallysize = db.GetLadderOption( self.ladder_id, "max_team_size" )
		for team in teamsdict:
			teamsize = teamsdict[team]
			if teamsize < minteamsize:
				return False
			if teamsize > maxteamsize:
				return False

		for ally in alliesdict:
			allysize = alliesdict[ally]
			if allysize < minallysize:
				return False
			if allysize > maxallysize:
				return False

		return True

	def CommitMatch(self,db):
		self.ParseSpringOutput()
		ladder = db.GetLadder(self.ladder_id )
		gameid = self.gameid
		if not self.CheckValidSetup( db ):
			raise InvalidOptionSetup( gameid, self.ladder_id )
		session = db.sessionmaker()
		match = Match()
		match.date 	= datetime.now()
		match.modname  = ''
		match.mapname = ''
		match.replay = ''
		match.game_id = gameid
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
		self.bots		= parseSec( getSectionContect( setup_section, 'AIS' 		) )
		self.allies		= parseSec( getSectionContect( setup_section, 'ALLYTEAMS' 	) )
		self.options 	= parseSec( getSectionContect( setup_section, 'OPTIONS' 	) )
		self.restr		= parseSec( getSectionContect( setup_section, 'RESTRICTIONS') )
		game_section 	= getSectionContect( self.springoutput, 'GAME' )
		num_players = len(self.teams)
		self.players = dict()
		if 'gameid' in self.options.keys():
			self.gameid = self.options['gameid']
		else:
			self.gameid = 'no game id found'

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

		#replace ai name with lib name
		tempplayers = dict()
		for playername in self.players:
			playercontent = self.players[playername]
			if playername in self.bots:
				playername = self.bots[playername]
			tempplayers[playername] = playercontent
		self.players = tempplayers
