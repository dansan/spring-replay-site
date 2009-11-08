# -*- coding: utf-8 -*-

from db_entities import *

class MatchResult(Object):

	def __init__( self, stdout, allies, teams, battle_users, battlefounder )
		self.springoutput 	= stdout
		self.allies 		= allies
		self.teams 			= teams
		self.battle_users 	= battle_users
		self.battlefounder 	= battlefounder

	