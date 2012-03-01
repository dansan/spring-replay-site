# -*- coding: utf-8 -*-
import time
import traceback
import zipfile
import zlib
import os

from tasbot.customlog import Log
import tasbot

from db_entities import *
from ranking import *
import demoparser
from script import Script
from myutils import mkdir_p


class InvalidOptionSetup( Exception ):
	def __init__(self, gameid, ladderid):
		self.gameid = gameid
		self.ladderid = ladderid

	def __str__(self):
		return "Setup for game %s did not match ladder rules for ladder %d" %(self.gameid,self.ladderid)

class UnterminatedReplayException( Exception ):
	def __init__(self, gameid, ladderid):
		self.gameid = gameid
		self.ladderid = ladderid

	def __str__(self):
		return "Replay for game %s, ladder %d, did not reach completion" %(self.gameid,self.ladderid)

class BannedPlayersDetectedException( Exception ):
	def __init__(self, bannedplayers ):
		self.bannedplayers = bannedplayers

	def __str__(self):
		return "The game had banned banned players (%s) in it and was not reported!" %(self.bannedplayers )


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

class MatchToDbWrapper:

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

	def CommitMatch(self,db, doValidation=True):
		self.ParseSpringOutput()
		ladder = db.GetLadder(self.ladder_id )
		gameid = self.gameid
		if doValidation and not self.CheckValidSetup( db ):
			raise InvalidOptionSetup( gameid, self.ladder_id )
		session = db.sessionmaker()
		match = Match()
		match.date 	= datetime.datetime.now()
		match.modname  = ''
		replayzip = os.path.basename(self.replay).replace(".sdf",".zip")
		base = tasbot.config.Config().get('ladder','base_dir')
		replayzip = os.path.join( base, 'demos', replayzip)
		mkdir_p(replayzip)
		with zipfile.ZipFile(replayzip, mode='w') as f_out:
			f_out.write(self.replay, compress_type=zipfile.ZIP_DEFLATED)
		match.replay = replayzip
		match.game_id = gameid
		match.ladder_id = ladder.id
		match.last_frame = self.game_over
		match.duration = datetime.timedelta( seconds=float(match.last_frame) / 30.0 )
		session.add( match )
		session.commit()
		#session.refresh()
		matchid = match.id
		match.mapname = ''
		for key,val in self.options.iteritems():
			s = MatchSetting()
			s.key = key
			s.value = val
			if key == "mapname":
				query = session.query( Map ).filter( Map.name == val )
				if query.count() == 0:
					import xmlrpcdl
					db_map = xmlrpcdl.DownloadQueue().add_map(val)
					session.add(db_map)
					session.commit()
				else:
					db_map = query.one()
				match.mapname = db_map.name
				session.add( match )
				session.commit()
			if key == "modname":
				match.modname = val
				session.add( match )
				session.commit()
			s.match_id = match.id
			session.add( s )
			#session.commit()
		for key,val in self.restrictions.iteritems():
			s = MatchSetting()
			s.key = key
			s.value = val
			s.match_id = match.id
			session.add( s )
			session.commit()
		self.CommitPlayerResults(session,match)
		session.close()
		GlobalRankingAlgoSelector.GetInstance( ladder.ranking_algo_id ).Update( ladder.id, match, db )
		return matchid

	def CommitPlayerResults(self,session,match):
		for name,result in self.players.iteritems():
			p = session.query( Player ).filter( Player.nick == name ).first()
			if not p:
				p = Player( name )
				session.add( p )
				session.commit()
			result.player_id = p.id
			result.match_id = match.id
			result.ladder_id = match.ladder_id
			result.date = match.date
			session.add( result )
			session.commit()


class AutomaticMatchToDbWrapper(MatchToDbWrapper):

	def __init__( self, replay, ladder_id ):
		self.replay = replay
		self.ladder_id		= ladder_id
		self.game_started	= False
		self.game_over		= -1

	def CheckvalidPlayerSetup( self, db ):
		laddername = db.GetLadderName( self.ladder_id )
		teamsdict = dict()
		alliesdict = dict()
		countedbots = []
		bannedplayers = []
		for player in self.teams:
			if not db.AccessCheck( self.ladder_id, player, Roles.User ):
				bannedplayers.append( player )
				continue
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
		if len(bannedplayers) != 0:
			raise BannedPlayersDetectedException( bannedplayers )
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
		maxallysize = db.GetLadderOption( self.ladder_id, "max_ally_size" )
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

	def ParseSpringOutput(self):
		with open(self.replay, 'rb') as demofile:
			parser = demoparser.DemoParser(demofile)
			script = Script(parser.getScript())
			open('/tmp/sc','w').write(parser.getScript())
			self.players = script.players
			self.bots = script.bots
			self.teams = script.teams
			self.allies = script.allies
			self.options = dict(script.modoptions.items() 
							+ script.other.items() + script.mapoptions.items())
			self.restrictions = script.restrictions
			self.gameid = 'no game id found'
			packet = True
			currentFrame = 0
			playerIDToName = {}
			kop = open('/tmp/msg.data','w')
			while packet:
				packet = parser.readPacket()
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
							if clean_name in script.spectators.keys():
								continue 
							playerIDToName[messageData['playerNum']] = clean_name 
							self.players[clean_name].connected = True
						elif messageData['cmd'] == 'startplaying' and messageData['countdown'] == 0:
							self.game_started = True
						elif messageData['cmd'] == 'gameover':
							if not self.game_started:
								Log.error( 'game not started on gameover found', 'Match.py' )
							else:
								self.game_over = currentFrame
						elif messageData['cmd'] == 'gameid':
							self.gameid = messageData['gameID']
						elif messageData['cmd'] == 'playerleft':
							playername = clean(messageData['playerName'])
							if clean_name in script.spectators.keys():
								continue
							if messageData['bIntended'] == 0:
								self.players[playername].timeout = True
							if messageData['bIntended'] == 1:
								self.players[playername].quit = True
							if messageData['bIntended'] == 2:
								self.players[playername].kicked = True
						elif messageData['cmd'] == 'team':
							if clean_name in script.spectators.keys():
								continue
							if messageData['action'] == 'team_died': #team died event
								deadTeam = messageData['param']
								for name,rank in self.players.iteritems():
									if rank.team == deadTeam:
										self.players[name].died = currentFrame
							elif messageData['action'] == 'giveaway': 
								#giving everything away == death 
								self.players[clean_name].died = currentFrame
				except Exception, e:
					Log.exception(e)
					raise e
	
			kop.close()
			if self.game_over < 0:
				raise UnterminatedReplayException( self.gameid, self.ladder_id )
			#replace ai name with lib name
#			tempplayers = dict()
#			for playername in self.players:
#				playercontent = self.players[playername]
#				if playername in self.bots:
#					playername = self.bots[playername]
#				tempplayers[playername] = playercontent
#			self.players = tempplayers

class ManualMatchToDbWrapper(MatchToDbWrapper):

	def __init__( self, playerlist, playerscores, teams, ladder_id, options, restrictions, bots, allies, allies_map, teams_map ):
		self.playerscores 	= playerscores
		self.playerlist		= playerlist
		self.ladder_id		= ladder_id
		self.game_started	= False
		self.game_over		= -1
		self.options		= options
		self.restrictions	= restrictions
		self.teams			= teams
		self.allies			= allies
		self.bots			= bots
		self.allies_map		= allies_map
		self.teams_map		= teams_map
		self.replay			= ""

	def CheckvalidPlayerSetup( self, db ):
		for p in self.playerscores.keys():
			if not p in self.playerlist:
				return False
		return True#we require a score for all players

	def ParseSpringOutput(self):
		#here we fake a lot of stuff to fit missing, but required, data
		num_players = len(self.teams)
		self.players = dict()
		self.gameid = int(time.time())
		#this is later used to set match.last_frame
		self.game_over = max( self.playerscores.itervalues() )
		self.game_started = True

		for name in self.playerlist:
			r = Result()
			#r.team = team
			r.connected = True
			#with earlier setting of game_over we emulate same relative scaling as with deaths = game frame no
			r.died = self.playerscores[ name ]
			r.team = self.teams_map[name]
			r.ally = self.allies_map[name]
			#everything else can stay on defaults (se db_entities.py)
			self.players[ name ] = r


		#replace ai name with lib name
		tempplayers = dict()
		for playername in self.players:
			playercontent = self.players[playername]
			if playername in self.bots:
				playername = self.bots[playername]
			tempplayers[playername] = playercontent
		self.players = tempplayers

