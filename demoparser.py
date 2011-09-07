import sys, struct, zlib, binascii, time, traceback, os

class DemoParser:
	DEMOFILE_MAGIC = 'spring demofile'
	DEMOFILE_VERSION = 4
	DEMOFILE_HEADERSIZE = 112

	headerTemplate = [
		'magic',
		'version',
		'headerSize',
		'versionString',
		'gameID',
		'unixTime',
		'scriptSize',
		'demoStreamSize',
		'gameTime',
		'wallclockTime',
		'numPlayers',
		'playerStatSize',
		'playerStatElemSize',
		'numTeams',
		'teamStatSize',
		'teamStatElemSize',
		'teamStatPeriod',
		'winningAllyTeam'
		]

	def __init__(self, handle):
		self.reference = {'header':0}
		self.header = {}
		self.handle = handle

		handle.seek(0)
		magic, version, headerSize = struct.unpack('<16s2i', handle.read(24))
		magic = magic.strip('\0')
		if magic != self.DEMOFILE_MAGIC or version != self.DEMOFILE_VERSION or headerSize != self.DEMOFILE_HEADERSIZE:
			print 'DemoParser Error: Header version mismatch or corrupt demo.'
			return
		header = dict(zip(self.headerTemplate, (magic, version, headerSize) + struct.unpack('<16s16sQ12i', handle.read(88))))

		lll = struct.unpack('<2Q', header['gameID']) # gameID is a long long long, which struct can't unpack :)
		header['gameID'] = (lll[0] << 8) + lll[1]

		for key in header: # strip null chars from unpacked strings
			value = header[key]
			if type(value) == str:
				header[key] = value.strip('\0')

		self.header = header
		self.reference['script'] = handle.tell()
		self.script = handle.read(header['scriptSize'])

		self.reference['demoStream'] = handle.tell()

		if not header['demoStreamSize']: return # game didn't actually end, so no stats.


		# should probably parse stats a little more
		playerStatSize = header['playerStatSize']
		teamStatSize = header['teamStatSize']
		handle.seek(-(playerStatSize+teamStatSize), 2)

		self.reference['playerStats'] = handle.tell()
		self.playerStats = handle.read(playerStatSize)

		self.reference['teamStats'] = handle.tell()
		self.teamStats = handle.read(teamStatSize)

		self.seek('demoStream')

	def read(self, length):
		return self.handle.read(length)

	def seek(self, location):
		if type(location) == str:
			self.handle.seek(self.reference[location])
		else: self.handle.seek(location)

	def tell(self): return self.handle.tell()

	def getHeader(self): return self.header
	def getScript(self): return self.script
	def getPlayerStats(self): return self.playerStats
	def getTeamStats(self): return self.teamStats

	def readPacket(self):
		maxSize = (self.header['demoStreamSize'] or sys.maxint)
		if maxSize:
			modGameTime, length = struct.unpack('<fI', self.read(8))
			if self.tell()+length - self.reference['demoStream'] == maxSize: return False
			data = self.read(length)
		if not data: return False
		return {'modGameTime':modGameTime, 'length':length, 'data':data}

def write(locals, *keys):
	#blacklist = ('newframe', 'playerinfo', 'luamsg', 'mapdraw', 'aicommand', 'playerstat')
	returnval = dict()
	if locals['cmd'] in blacklist: return
	for key in keys:
		item = locals[key]
		returnval[key] = item
	return returnval

class PlayerDict(dict):
	def __getitem__(self, item):
		return dict.__getitem__(self, item) if item in self else None

players = PlayerDict()

def parsePacket(packet):
	if not packet or not packet['data']: return
	data = packet['data']

	cmd = ord(data[0])
	data = data[1:]
	if cmd == 1:
		cmd = 'keyframe'
		framenum = struct.unpack('<i', data)[0]
		return write(locals(), 'cmd', 'framenum')
	elif cmd == 2:
		cmd = 'newframe'
		return write(locals(), 'cmd')
	elif cmd == 3:
		cmd = 'quit'
		return write(locals(), 'cmd')
	elif cmd == 4:
		cmd = 'startplaying'
		countdown = struct.unpack('<I', data)[0]
		return write(locals(), 'cmd', 'countdown')
	elif cmd == 5:
		cmd = 'setplayernum'
		playerNum = ord(data)
		return write(locals(), 'cmd', 'playerNum')
	elif cmd == 6:
		cmd = 'setplayername'
		size, playerNum = struct.unpack('<BB', data[:2])
		playerName = data[2:]
		if not playerNum in players:
			players[playerNum] = playerName.strip('\0')
		return write(locals(), 'cmd', 'size', 'playerNum', 'playerName')
	elif cmd == 7:
		cmd = 'chat'
		size, fromID, toID = struct.unpack('<3B', data[:3])
		message = data[3:]
		playerName = players[fromID] or ''
		return write(locals(), 'cmd', 'size', 'fromID', 'playerName', 'toID', 'message')
	elif cmd == 8:
		cmd = 'randseed'
		randSeed = struct.unpack('<I', data)[0]
		return write(locals(), 'cmd', 'randSeed')
	elif cmd == 9:
		cmd = 'gameid'
		lll = struct.unpack('<2Q', data) # gameID is a long long long, which struct can't unpack :)
		gameID = (lll[0] << 8) + lll[1]
		return write(locals(), 'cmd', 'gameID')
	elif cmd == 11:
		cmd = 'command'
		size, playerNum, cmdID, options = struct.unpack('<hBiB', data[:8])
		params = struct.unpack('<%if'%((len(data)-6)/4), data[8:])
		playerName = players[playerNum] or ''
		return write(locals(), 'cmd', 'size', 'playerNum', 'playerName', 'cmdID', 'options', 'params')
	elif cmd == 12:
		cmd = 'select'
		size, playerNum = struct.unpack('<hB', data[:3])
		selectedUnitIDs = struct.unpack('<%ih'%((len(data)-3)/2), data[3:])
		playerName = players[playerNum] or ''
		return write(locals(), 'cmd', 'size', 'playerNum', 'playerName', 'selectedUnitIDs')
	elif cmd == 13:
		cmd = 'pause'
		playerNum, bPaused = struct.unpack('<BB', data)
		playerName = players[playerNum] or ''
		return write(locals(), 'cmd', 'playerNum', 'playerName', 'bPaused')
	elif cmd == 14:
		cmd = 'aicommand'
		size, playerNum, unitID, aiID, options = struct.unpack('<hBhiB', data[:10])
		params = struct.unpack('<%if'%((len(data)-10)/4), data[10:])
		playerName = players[playerNum] or ''
		return write(locals(), 'cmd', 'size', 'playerNum', 'playerName', 'unitID', 'aiID', 'options', 'params')
	elif cmd == 15:
		cmd = 'aicommands'
		msgsize, playerNum, unitIDCount = struct.unpack('<hBh', data[:5])
		pos = (unitIDCount*2)+5
		unitIDs = struct.unpack('<%ih'%(unitIDCount), data[5:pos])
		commandCount = struct.unpack('<h', data[pos:pos+2])[0]
		pos += 2
		commands = []
		for i in xrange(commandCount):
			cmdID, options, size = struct.unpack('<iBh', data[pos:pos+7])
			pos += 7
			params = struct.unpack('<%if'%size, data[pos:pos+(4*size)])
			pos += 4*size
			commands.append((cmdID, options, size, params))
		playerName = players[playerNum] or ''
		return write(locals(), 'cmd', 'msgsize', 'playerNum', 'playerName', 'unitIDCount', 'unitIDs', 'commands')
	elif cmd == 16:
		cmd = 'aishare'
		playerNum, sourceTeam, destTeam, metal, energy, unitIDCount = struct.unpack('<3Bffh', data[13:])
		unitIDs = struct.unpack('<%ih'%unitIDCount, data[:13])
		playerName = players[playerNum] or ''
		return write(locals(), 'cmd', 'playerNum', 'playerName', 'sourceTeam', 'destTeam', 'metal', 'energy', 'unitIDCount', 'unitIDs')
	elif cmd == 17:
		cmd = 'memdump'
		print 'OMG A MEMORY DUMP'
		return write(locals(), 'cmd')
	elif cmd == 19:
		cmd = 'user_speed'
		playerNum, userSpeed = struct.unpack('<Bf', data)
		playerName = players[playerNum] or ''
		return write(locals(), 'cmd', 'playerNum', 'playerName', 'userSpeed')
	elif cmd == 20:
		cmd = 'internal_speed'
		internalSpeed = struct.unpack('<f', data)[0]
		return write(locals(), 'cmd', 'internalSpeed')
	elif cmd == 21:
		cmd = 'cpu_usage'
		cpuUsage = struct.unpack('<f', data)[0]
		return write(locals(), 'cmd', 'cpuUsage')
	elif cmd == 22:
		cmd = 'direct_control'
		playerNum = ord(data)
		playerName = players[playerNum] or ''
		return write(locals(), 'cmd', 'playerNum', 'playerName')
	elif cmd == 23:
		cmd = 'dc_update'
		playerNum, status, heading, pitch = struct.unpack('<BBhh', data)
		playerName = players[playerNum] or ''
		return write(locals(), 'cmd', 'playerNum', 'playerName', 'status', 'heading', 'pitch')
	elif cmd == 25:
		cmd = 'attemptconnect'
		size = struct.unpack('<H', data[0])[0]
		name, password, version = data[1:].split('\0',2)
		version = version.strip('\0')
		return write(locals(), 'cmd', 'size', 'name', 'password', 'version')
	elif cmd == 26:
		cmd = 'share'
		playerNum, shareTeam, shareUnits, shareMetal, shareEnergy = struct.unpack('<3Bff', data)
		playerName = players[playerNum] or ''
		return write(locals(), 'cmd', 'playerNum', 'playerName', 'shareTeam', 'shareUnits', 'shareMetal', 'shareEnergy')
	elif cmd == 27:
		cmd = 'setshare'
		playerNum, team, metalShareFraction, energyShareFraction = struct.unpack('<BBff', data)
		playerName = players[playerNum] or ''
		return write(locals(), 'cmd', 'playerNum', 'playerName', 'team', 'metalShareFraction', 'energyShareFraction')
	elif cmd == 28:
		cmd = 'sendplayerstat'
		return write(locals(), 'cmd')
	elif cmd == 29:
		cmd = 'playerstat' # fails
		#playerNum, wtf = struct.unpack()
		data = 'unparsed'
		return write(locals(), 'cmd', 'data')
	elif cmd == 30:
		cmd = 'gameover'
		return write(locals(), 'cmd')
	elif cmd == 31: # okay, this fails on 0.80.x ... gotta check why.
		cmd = 'mapdraw'
		data = 'unparsed'
		return write(locals(), 'cmd', 'data')
		size, playerNum, command = struct.unpack('<3B', data[:3])
		data = data[3:]
		if command == 0: # point = 0, erase = 1, line = 2
			x, z = struct.unpack('<hh', data[:4])
			label = data[4:]
		elif command == 1:
			x, z = struct.unpack('<hh', data)
		elif command == 2:
			x1, z1, x2, z2 = struct.unpack('<4hx', data)
	elif cmd == 33:
		cmd = 'syncresponse'
		playerNum, frameNum, checksum = struct.unpack('<BiI', data)
		playerName = players[playerNum] or ''
		return write(locals(), 'cmd', 'playerNum', 'playerName', 'frameNum', 'checksum')
	elif cmd == 35:
		cmd = 'systemmsg'
		size, playerNum = struct.unpack('<BB', data[:2])
		message = data[2:]
		playerName = players[playerNum] or ''
		return write(locals(), 'cmd', 'size', 'playerNum', 'playerName', 'message')
	elif cmd == 36:
		cmd = 'startpos'
		playerNum, team, ready, x, y, z = struct.unpack('<3B3f', data) # ready - 0 = not ready, 1 = ready, 2 = don't update readiness
		playerName = players[playerNum] or ''
		return write(locals(), 'cmd', 'playerNum', 'playerName', 'team', 'ready', 'x', 'y', 'z')
	elif cmd == 38:
		cmd = 'playerinfo'
		playerNum, cpuUsage, ping = struct.unpack('<BfI', data) # ping is in number of frames
		playerName = players[playerNum] or ''
		return write(locals(), 'cmd', 'playerNum', 'playerName', 'cpuUsage', 'ping')
	elif cmd == 39:
		cmd = 'playerleft'
		playerNum, bIntended = struct.unpack('<BB', data) # 0 = lost connection, 1 = left, 2 = forced (kicked)
		readableIntended = {0: 'lost connection', 1: 'left', 2:'forced (kicked)'}[bIntended]
		playerName = players[playerNum] or ''
		return write(locals(), 'cmd', 'playerNum', 'playerName', 'bIntended', 'readableIntended')
	elif cmd == 50:
		cmd = 'luamsg'
		size, playerNum, script, mode = struct.unpack('<HBHB', data[:6])
		msg = data[6:]
		playerName = players[playerNum] or ''
		return write(locals(), 'cmd', 'size', 'playerNum', 'playerName', 'script', 'mode', 'msg')
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
			# team which had died (sent by all players to prevent cheating)
		elif action == 5:
			action = 'ai_created'
			# team which is now controlled by a skirmish AI
		elif action == 6:
			action = 'ai_destroyed'
			# team which had its controlling skirmish AI be destroyed
		playerName = players[playerNum] or ''
		return write(locals(), 'cmd', 'playerNum', 'playerName', 'action', 'param')
	elif cmd == 52:
		cmd = 'gamedata'
		#f = open('gamedata.dat', 'wb')
		#f.return write(chr(52)+data)
		#f.close()
		size, compressedSize = struct.unpack('<HH', data[:4])
		setupText = zlib.decompress(data[4:compressedSize+4])
		data = data[compressedSize+4:]
		#print data
		#print __import__('binascii').hexlify(data)
		#return
		#mapName, modName, data = data.split('\0', 2)
		#print mapName, modName
		if len(data) == 12: # 0.80 or later
			mapChecksum, modChecksum, randomSeed = struct.unpack('<3i', data)
			return write(locals(), 'cmd', 'size', 'compressedSize', 'setupText', 'mapChecksum', 'modChecksum', 'randomSeed')
		elif False:
			print __import__('binascii').hexlify(data)
			script, mapName, modName, data = data.split('\0', 3)
			print script, mapName, modName
			print len(data)
			mapChecksum, modChecksum, randomSeed = struct.unpack('<3i', data)
			print mapChecksum, modChecksum, randomSeed
		#print size, compressedSize, setupText, mapChecksum, modChecksum, randomSeed
		else:
			data = 'unparsed, old replay format'
			return write(locals(), 'cmd', 'data')
	elif cmd == 53:
		cmd = 'alliance'
		playerNum, otherAllyTeam, allianceState = struct.unpack('<3B', data) # 0 = not allied, 1 = allied
		readableAllianceState = {0: 'not allied', 1: 'allied'}[allianceState]
		playerName = players[playerNum] or ''
		return write(locals(), 'cmd', 'playerNum', 'playerName', 'otherAllyTeam', 'allianceState', 'readableAllianceState')
	elif cmd == 54:
		cmd = 'ccommand'
		size, playerNum = struct.unpack('<Hi', data[:6])
		command, extra = data[6:].split('\0',1)
		playerName = players[playerNum] or ''
		return write(locals(), 'cmd', 'size', 'playerNum', 'playerName', 'command', 'extra')
	elif cmd == 60:
		cmd = 'teamstat'
		data = 'unparsed'
		return write(locals(), 'cmd', 'data')
