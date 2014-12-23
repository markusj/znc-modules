# titlebot.py

# a bot to vote about a topic (podcast title)
# used in freenode/##happyshooting

import znc
#from collections import deque



class VotingOption:
	# id
	# text			string
	# votes			int
	# deleted		boolean
	
	def __init__(self, id, text):
		self.id = id
		self.text = text
		self.votes = 0
		self.deleted = False



class NickWrapper:
	# nick			string
	# ident			string
	# host			string
	
	# znick: znc.Nick
	def __init__(self, znick):
		self.nick = str(znick.GetNick())
		self.ident = str(znick.GetIdent())
		self.host = str(znick.GetHost())


class WhoisData:
	# nick			string
	# ident			string
	# host			string
	# nickuser		string
	# valid			boolean
	# error			boolean
	
	def __init__(self):
		self.nick = None
		self.ident = None
		self.host = None
		self.nickuser = None
		self.valid = False
		self.error = False



class UserInfo:
	# mod			titlebot
	# id			int
	# nick			string
	# ident			string
	# host			string
	# nickuser		string
	# stale			boolean
	
	def __init__(self, mod, nickw):
		self.mod = mod
		self.readNickWrapper(nickw)
		self.nickuser = None
		self.stale = False
		# issue a whois request to figure out if the user is authed
		self.authWhois()
		# assign id only if all previous steps succeeded 
		self.id = len(mod.userdb)
		# add to user databases
		self.addToDBs()
	
	
	def readNickWrapper(self, nickw):
		self.nick = nickw.nick
		self.ident = nickw.ident
		self.host = nickw.host
	
	
	def readWhoisData(self, whoisData):
		self.removeFromDBs() # remove before old keys are lost
		
		self.nick = whoisData.nick
		self.ident = whoisData.ident
		self.host = whoisData.host
		self.nickuser = whoisData.nickuser
		
		self.addToDBs() # re-insert with new keys
	
	
	def addToDBs(self):
		self.mod.userdb[self.id] = self
		self.mod.activeNicks[self.nick] = self.id
		if self.nick in self.mod.nickdb:
			self.mod.nickdb[self.nick].append(self.id)
		else:
			self.mod.nickdb[self.nick] = [ self.id ]
		self.mod.hostdb[self.host] = self.id # assumption: host is unique
	
	
	def removeFromDBs(self):
		if self.id in self.mod.userdb: # not really required ...
			del self.mod.userdb[self.id]
		if self.nick in self.mod.activeNicks:
			del self.mod.activeNicks[self.nick]
		if self.nick in self.mod.nickdb and self.id in self.mod.nickdb[self.nick]:
			self.mod.nickdb[self.nick].remove(self.id)
		if self.host in self.mod.hostdb:
			del self.mod.hostdb[self.host]
	
	
	# assert whoisData.valid
	# return boolean accepted?
	def claim(self, whoisData):
		if not self.stale:
			# assert: self.nick points always to the same (valid) IRC user
			# not stale. nick either matches or the claim must be invalid
			return self.nick == whoisData.nick
		
		if self.nickuser is None and self.host == whoisData.host:
			# fast path, try to avoid a whois query if possible
			# update/reassign to new nick
			self.readWhoisData(whoisData)
			self.stale = False
			
			return True
			
		if whoisData.nickuser is None:
			# no direct match and whois did not justify the claim -> reject
			return False
		elif whoisData.nickuser != self.nick and whoisData.nickuser != self.nickuser:
			# whois does not match nick or nickuser -> reject
			return False
		else:
			# whois either matched nick or nickuser -> claim is valid, accept
			readWhoisData(whoisData)
			self.stale = False
		
			return True
	
	
	def authWhois(self):
		self.mod.requestWhois(self.nick, self.whoisCallback)
	
	
	# nick: string, error: boolean
	def whoisCallback(self, nick, error):
		if not error and nick in self.mod.whoisdb:
			whoisData = self.mod.whoisdb[nick]
			
			self.nickuser = whoisData.nickuser



class ChanInfo:
	# mod			titlebot
	# name			string
	# activator		string , len(activator) == 1
	# admins		list of string
	# options		list of VotingOption
	# userVotes		dict userId -> index for options
	# enabled		boolean
	
	def __init__(self, mod, chanName, activator, adminList):
		self.mod = mod
		self.name = chanName
		self.activator = activator
		self.admins = adminList
		self.options = [ ]
		self.userVotes = { }
		self.enabled = False
	
	# voting: enable, disable, reset, vote, revoke
	# i/o: print options, votes, results
	
	def reset(self):
		self.options.clear()
		self.userVotes.clear()
		self.enabled = False
	
	
	# user: UserInfo
	def isAdmin(self, user):
		#return not user.stale and (user.nick in self.admins or user.nickuser in self.admins)
		return not user.stale and user.nickuser in self.admins # admins are required to be authenticated against nickserv
	
	
	# user: int, option: int -> int ( >= 0: ACK, -1: No such option, <-1: -oldVote - 2)
	def vote(self, user, option):
		if len(self.options) <= option or self.options[option].deleted:
			return -1
		
		oldVote = self.userVotes.get(user)
		
		if oldVote is not None:
			return -oldVote - 2
		
		self.options[option].votes += 1
		self.userVotes[user] = option
		
		return option
	
	
	# user: int -> int
	def revoke(self, user):
		oldVote = self.userVotes.get(user)
		
		if oldVote is None:
			return -1
		
		self.options[oldVote].votes -= 1
		del self.userVotes[user]
		
		return oldVote
	
	
	# option: str -> int
	def addOption(self, option):
		result = len(self.options)
		newOption = VotingOption(result, option)
		
		self.options.append(newOption)
		
		return result
	
	
	# option: int -> list of userId
	def delOption(self, option):
		if option >= len(self.options) or self.options[option].deleted:
			return None
		
		voteOpt = self.options[option]
		result = [ ]
		
		for uid, opt in self.userVotes.items():
			if option == opt:
				result.append(uid)
				voteOpt.votes -= 1
		
		for uid in result:
			del self.userVotes[uid]
		
		voteOpt.deleted = True
		
		return result



class titlebot(znc.Module):
	description = "A voting bot"
	module_types = [ znc.CModInfo.NetworkModule ]
	has_args = True
	args_help_text = "A list of channels and administrative users, format <channel> <activator_char> <user> <more users> : <channel> ..."
	
	# chans				dict channel -> ChanInfo
	# userdb			dict userId -> UserInfo
	# activeNicks		dict nick -> userId
	# nickdb 			dict nick -> list of userId
	# hostdb			dict hostname -> list of userId
	# whoisdb			dict nick -> WhoisData
	# whoisCallbacks 	dict nick -> list callback(string nick, bool error)
	
	def __init__(self):
		self.chans = { }
		self.userdb = { }
		self.activeNicks = { }
		self.nickdb = { }
		self.hostdb = { }
		self.whoisdb = { }
		self.whoisCallbacks = { }
	
	
	# assert whoisdb[nickw.nick].valid
	def lookup(self, nickw):
		sNick = nickw.nick
		sHost = nickw.host
		
		# easy case: request for an active nick
		if sNick in self.activeNicks:
			return self.userdb[self.activeNicks[sNick]]
		# else: difficult case. search for a matching stale nick first
		if sNick in self.nickdb:
			nickUsers = self.nickdb[sNick]
			
			for userId in nickUsers:
				userInfo = self.userdb[userId]
				
				if userInfo.claim(self.whoisdb[sNick]):
					return userInfo
		
		# else: could not claim any user with the same nick, fall back to host
		if sHost in self.hostdb:
			userId = self.hostdb[sHost]
			userInfo = self.userdb[userId]
			
			if userInfo.claim(self.whoisdb[sNick]):
				return userInfo
			else: # there exists a user from the same host but claim failed. REJECT!
				return None
		
		# else: no matching host found, add new user
		return UserInfo(self, nickw)
	
	
	# sNick: str, callback: function(string nick, bool error)
	def requestWhois(self, sNick, callback):
		if sNick in self.whoisdb:
			# there is already a whois record for this nick
			if self.whoisdb[sNick].valid:
				callback(sNick, False)
				return
		else: # request whois data
			self.whoisdb[sNick] = WhoisData()
			
			self.PutIRC("WHOIS " + sNick)
		
		# whois is in flight, add listeners
		if sNick in self.whoisCallbacks:
			nickListeners = self.whoisCallbacks[sNick]
		else:
			nickListeners = [ ]
			self.whoisCallbacks[sNick] = nickListeners
		
		nickListeners.append(callback)
	
	
	def reset(self):
		for chanInfo in self.chans.values():
			chanInfo.reset()
		
		self.userdb.clear()
		self.activeNicks.clear()
		self.nickdb.clear()
		self.hostdb.clear()
		self.whoisdb.clear()
		self.whoisCallbacks.clear()
	
	
	# [] admin only
	# help <channel> [public | admin]
	# vote <channel> <num>
	# revoke <channel> [user]
	# add <channel> <text>
	# [del <channel> <num>]
	# 
	# auth <channel>
	# [enable <channel>]
	# [disable <channel>]
	# [reset <channel>]
	#
	# list <channel> [results|votes] [public]
	def parseMessage(self, message, nick=None, channel=None, console=False):
		if nick is None: # mod console, use own nick
			nick = self.GetNetwork().GetIRCNick()
		sNick = str(nick.GetNick())
		
		tokens = str(message).split(None)
		strippedTokens = 0
		
		if len(tokens) == 0:
			return # nothing to do
		
		if len(tokens) > 1:
			# test if token[1] contains the channel name
			if len(tokens[1]) > 1 and tokens[1][0] == "#":
				chanName = tokens[1]
				messageChan = self.GetNetwork().FindChan(chanName)
				# test if nick is in this channel
				if console or messageChan.FindNick(sNick) is not None:
					channel = messageChan
					del tokens[1] # remove the channel name to unify/simplify parsing
					strippedTokens += 1
				else:
					self.sendmsg(sNick, "I do only accept commands from users in my channels")
					return
		
		# no channel name so far? try to derive it from our common channels
		if channel is None:
			commonChans = znc.VChannels()
			nick.GetCommonChans(commonChans, self.GetNetwork())
		
			if len(commonChans) != 1:
				self.sendmsg(sNick, "Which channel did you mean? Please send your command as: <COMMAND> <CHANNEL> <ARGS>")
				return
			
			channel = commonChans[0]
		
		if channel.GetName() in self.chans:
			chan = self.chans[str(channel.GetName())]
		else:
			self.sendmsg(sNick, "I do not listen to commands for this channel")
			return
		
		# we are set and ready to parse the commands: message/tokens, nick, channel
		cmd = tokens[0].lower()
		del tokens[0]
		strippedTokens += 1
		sChan = str(channel.GetName())
		nickw = NickWrapper(nick)
		runCmd = None
		errStr = ""
		userRequired = True
		adminRequired = True
		
		if cmd == "help":
			if len(tokens) == 0:
				userRequirec = False
				adminRequired = False
				runCmd = lambda :self.printHelp(sNick, chan)
			else:
				arg = tokens[0].lower()
				
				if arg == "public":
					runCmd = lambda :self.printHelp(sChan, chan)
				elif arg == "admin":
					runCmd = lambda :self.printHelp(sNick, chan, True)
		elif cmd == "vote":
			if len(tokens) > 0 and tokens[0].isdigit():
				adminRequired = False
				runCmd = lambda :self.userVote(sNick, chan, int(tokens[0]))
		elif cmd == "revoke":
			if len(tokens) > 0:
				if tokens[0].isdigit():
					runCmd = lambda :self.userRevoke(sNick, int(tokens[0]), chan, True)
			else:
				adminRequired = False
				runCmd = lambda :self.userRevoke(sNick, None, chan)
		elif cmd == "add":
			if len(tokens) > 0:
				adminRequired = False
				runCmd = lambda :self.optionAdd(sNick, chan, str(message).split(None, strippedTokens)[strippedTokens])
		elif cmd == "del":
			if len(tokens) > 0 and tokens[0].isdigit():
				runCmd = lambda :self.optionDel(sNick, chan, int(tokens[0]))
		elif cmd == "auth":
			adminRequired = False
			runCmd = lambda :self.userAuth(sNick)
		elif cmd == "userdel":
			if len(tokens) > 0 and tokens[0].isdigit():
				runCmd = lambda :self.userDelete(int(tokens[0]), sNick)
		elif cmd == "enable":
			runCmd = lambda :self.voteSetEnabled(sNick, chan, True)
		elif cmd == "disable":
			runCmd = lambda :self.voteSetEnabled(sNick, chan, False)
		elif cmd == "reset":
			runCmd = lambda :self.voteReset(sNick, chan)
		elif cmd == "list":
			if len(tokens) > 0:
				tokens[0] = tokens[0].lower()
				printer = None
				
				if tokens[0] == "results":
					printer = lambda public:self.printResults(sNick, chan, public)
					del tokens[0]
				elif tokens[0] == "votes":
					printer = lambda public:self.printVotes(sNick, chan, public)
					del tokens[0]
				elif tokens[0] == "users":
					printer = lambda public:self.printUsers(sNick, chan)
					del tokens[0]
				elif tokens[0] == "public":
					runCmd = lambda :self.printOptions(sNick, chan, True)
				
				if printer is not None:
					if len(tokens) > 0 and tokens[0].lower() == "public":
						runCmd = lambda :printer(True)
					else:
						runCmd = lambda :printer(False)
			else:
				userRequired = False
				adminRequired = False
				runCmd = lambda :self.printOptions(sNick, chan, False)
		else:
			return # bad command, ignore
		
		if runCmd is None:
			self.sendmsg(sNick, "Bad or missing argument. " + errStr)
			return
		
		# setup callback and issue it
		userRequired |= adminRequired
		
		self.requestWhois(sNick, lambda whoisNick, error :self.executeMessage(nickw, chan, userRequired, adminRequired, runCmd, error))
	
	
	# nick: NickWrapper, chan: ChanInfo, userRequired: boolean, adminRequired: boolean, runCmd: function(), error: boolean
	def executeMessage(self, nickw, chan, userRequired, adminRequired, runCmd, error):
		if error:
			self.sendmsg(nickw.nick, "Error, failed to identify you. This is a bug and not your fault. Sorry!")
		
		user = self.lookup(nickw)
		
		if userRequired and user is None:
			self.sendmsg(nickw.nick, "Access denied. I think this nick belongs to someone else. If you believe this is wrong, please authentify yourself at NickServ or ask the bot administrators for help.")
			return
			
		if adminRequired and not chan.isAdmin(user):
			self.sendmsg(nickw.nick, "Access denied. Administrator privileges are required to run this command.")
			return
		
		runCmd()
	
	
	# to: string, chan: ChanInfo
	def printHelp(self, to, chan, admin=False):
		self.sendmsg(to, "If you send a command from a channel, you need to prepend the character " + chan.activator)
		self.sendmsg(to, "The argument <channel> is only required if you send the command as query/direct message.")
		self.sendmsg(to, "Arguments in [square brackets] are optional, the vertical bar | aka \"pipe\" denotes a choice between options")

		self.sendmsg(to, "  help   <channel>")
		self.sendmsg(to, "  vote   <channel> <option_id>     Vote for option <option_id>")
		self.sendmsg(to, "  revoke <channel>                 Revoke vote")
		self.sendmsg(to, "  add    <channel> <option_text>   Add voting option with <option_text>")
		self.sendmsg(to, "  list   <channel>                 Lists all voting options")
		self.sendmsg(to, "  auth   <channel>                 Authentify yourself. Use this if you identified yourself to NickServ after you have used this bot. Prevents others from stealing your vote")
		
		if not admin:
			return # do not print admin help
		
		self.sendmsg(to, "Additional or enhanced commands for administrators only")
		self.sendmsg(to, "  help    <channel> [public | admin]  Print help public in channel or print admin help")
		self.sendmsg(to, "  revoke  <channel> [<user_id>]       Revoke vote")
		self.sendmsg(to, "  del     <channel> <option_id>       Delete voting option <option_id>")
		self.sendmsg(to, "  userdel <channel> <user_id>         Delete the user from all internate databases and revoke his votes")
		self.sendmsg(to, "  enable  <channel>                   Enable/resume voting")
		self.sendmsg(to, "  disable <channel>                   Disable/pause voting. Voting might be continued later")
		self.sendmsg(to, "  reset   <channel>                   Resets the voting, drops all options and votes")
		self.sendmsg(to, "  list    <channel> [results | votes | users] [public]  Lists voting results, votes or users, optionally public in channel")
	
	
	# sNick: string
	def userAuth(self, sNick):
		# assert sNick in activeNicks
		userId = self.activeNicks[sNick]
		userInfo = self.userdb[userId]
		
		if userInfo.nickuser is not None:
			self.sendmsg(sNick, "You have already been authentified")
			return
		
		# delete whois entry if existing
		if sNick in self.whoisdb:
			del self.whoisdb[sNick]
		# and fetch new whois information
		self.requestWhois(sNick, self.userAuthWorker)
	
	
	def userAuthWorker(self, sNick, error):
		if error:
			self.sendmsg(sNick, "Error: Failed to gather whois information")
			return
		
		if sNick in self.whoisdb:
			# assert sNick in activeNicks
			userId = self.activeNicks[sNick]
			userInfo = self.userdb[userId]
			userInfo.readWhoisData(self.whoisdb[sNick])
		else:
			self.sendmsg(sNick, "Error: Expected to have whois information about you, but this was not the case.")
	
	
	# sNick: string, chanInfo: ChanInfo, option:int
	def userVote(self, sNick, chanInfo, option):
		userId = self.activeNicks[sNick]
		
		if not chanInfo.enabled:
			self.sendmsg(sNick, "Voting has been disabled")
			return
		
		result = chanInfo.vote(userId, option - 1)
		
		if result == option - 1:
			self.sendmsg(sNick, "Vote for option " + str(option) + " accepted")
		elif result == -1:
			self.sendmsg(sNick, "Failed: There is no such option. Maybe it has been deleted?")
		else:
			self.sendmsg(sNick, "Vote rejected, you have already voted for option " + str(-result - 1))
	
	
	# sNick: string, userId: int, chanInfo: ChanInfo, admin: boolean
	def userRevoke(self, sNick, userId, chanInfo, admin=False):
		userNick = sNick
			
		if userId is None: # allowed
			userId = self.activeNicks[userNick]
		else:
			if userId not in self.userdb:
				self.sendmsg(sAdmin, "Unknown user id: " + str(userId))
				return
			
			userNick = self.userdb[userId].nick
			
		msgTo = sNick if not admin else chanInfo.name
		
		if not chanInfo.enabled and not admin:
			self.sendmsg(sNick, "Voting has been disabled")
			return
		
		result = chanInfo.revoke(userId)
		
		if result >= 0:
			self.sendmsg(msgTo, "Vote by user " + sNick + " for option " + str(result + 1) + " has been revoked")
		else:
			self.sendmsg(sNick, "Failed: No vote to revoke for user " + sNick)
	
	
	# sNick: string, chanInfo: ChanInfo, option: string
	def optionAdd(self, sNick, chanInfo, option):
		if not chanInfo.enabled:
			self.sendmsg(sNick, "Voting has been disabled")
			return
		
		result = chanInfo.addOption(option)
		
		if result >= 0:
			self.sendmsg(chanInfo.name, "----- Option " + str(result + 1) + " added: " + option)
		else:
			self.sendmsg(sNick, "Failed to add option")
	
	
	# sNick: string, chanInfo: ChanInfo, option: int
	def optionDel(self, sNick, chanInfo, option):
		revoked = chanInfo.delOption(option - 1)
		
		if revoked is not None:
			for uid in revoked:
				userInfo = self.userdb[uid]
				
				self.sendmsg(chanInfo.name, "----- Vote by user " + userInfo.nick + " for option " + str(option) + " has been revoked -----")
				
			self.sendmsg(chanInfo.name, "----- Option " + str(option) + " has been deleted from admin " + sNick + " -----")
		else:
			self.sendmsg(sNick, "Failed to delete option. Does it exist or has it already been deleted by someone else?")
	
	
	# userId: int, sAdmin: string
	def userDelete(self, userId, sAdmin):
		if userId not in self.userdb:
			self.sendmsg(sAdmin, "Unknown user id: " + str(userId))
			return
		
		userInfo = self.userdb[userId]
		sNick = userInfo.nick
		
		# revoke all votes
		for chanInfo in self.chans.values():
			if userId in chanInfo.userVotes:
				result = chanInfo.revoke(userId)
				self.sendmsg(chanInfo.name, "Vote by user " + sNick + " for option " + str(result + 1) + " has been revoked")
		
		# and delete all user related records
		userInfo.removeFromDBs()
		if sNick in self.whoisdb:
			del self.whoisdb[sNick]
		if sNick in self.whoisCallbacks:
			del self.whoisCallbacks[sNick]
		
		self.sendmsg(sAdmin, "User " + sNick + " has been deleted from all databases")
	
	
	# sNick: string, chanInfo: ChanInfo, enabled: boolean
	def voteSetEnabled(self, sNick, chanInfo, enabled):
		if not chanInfo.enabled and enabled:
			self.sendmsg(chanInfo.name, "----- Voting has been ENABLED! -----")
		elif chanInfo.enabled and not enabled:
			self.sendmsg(chanInfo.name, "----- Voting has been DISABLED! -----")
		else:
			self.sendmsg(sNick, "Voting was already " + "enabled" if enabled else "disabled")
			
		chanInfo.enabled = enabled
	
	
	# sNick: string, chanInfo: ChanInfo
	def voteReset(self, sNick, chanInfo):
		chanInfo.reset()
		
		self.sendmsg(chanInfo.name, "All votes have been reset")
	
	
	# sNick: string, chanInfo: ChanInfo, public: boolean
	def printOptions(self, sNick, chanInfo, public):
		msgTo = sNick if not public else chanInfo.name
		
		self.sendmsg(msgTo, "----- Vote options (first number: id) -----")
		
		for option in chanInfo.options:
			if not option.deleted:
				self.sendmsg(msgTo, "  " + str(option.id + 1) + ") " + option.text + " (" + str(option.votes) + " votes)")
		
		self.sendmsg(msgTo, "----- Vote options end -----")
	
	
	# sNick: string, chanInfo: ChanInfo, public: boolean
	def printResults(self, sNick, chanInfo, public):
		msgTo = sNick if not public else chanInfo.name
		
		options = chanInfo.options.copy()
		options.sort(key=lambda option :option.votes, reverse=True)
		
		self.sendmsg(msgTo, "----- Vote results (first number is the placement, NOT the id) -----")
		
		index = 1
		for option in options:
			if not option.deleted:
				self.sendmsg(msgTo, "  " + str(index) + ". " + option.text + " (Option " + str(option.id + 1) + " with " + str(option.votes) + " votes)")
				index += 1
		
		self.sendmsg(msgTo, "----- Vote results end -----")
	
	
	# sNick: string, chanInfo: ChanInfo, public: boolean
	def printVotes(self, sNick, chanInfo, public):
		msgTo = sNick if not public else chanInfo.name
		options = [ ]
		
		for i in range(len(chanInfo.options)):
			options.append([ ])
		
		for userId, optionId in chanInfo.userVotes.items():
			options[optionId].append(userId)
		
		self.sendmsg(msgTo, "----- Vote list begin -----")
		
		for optionId, userIds in enumerate(options):
			option = chanInfo.options[optionId]
			# assert not option.deleted
			self.sendmsg(msgTo, "  Option " + str(optionId + 1) + ": " + option.text)
			
			for userId in userIds:
				userInfo = self.userdb[userId]
				
				self.sendmsg(msgTo, "    " + str(userInfo.id) + ": " + userInfo.nick + "!" + userInfo.ident + "@" + userInfo.host + " known as " + str(userInfo.nickuser) + " stale=" + str(userInfo.stale))
		
		self.sendmsg(msgTo, "----- Vote list end -----")
	
	
	# sNick: string, chanInfo: ChanInfo
	def printUsers(self, sNick, chanInfo):
		self.sendmsg(sNick, "----- Known user list begin -----")
		
		for userInfo in self.userdb.values():
			self.sendmsg(sNick, "  " + str(userInfo.id) + ": " + userInfo.nick + "!" + userInfo.ident + "@" + userInfo.host + " known as " + str(userInfo.nickuser) + " stale=" + str(userInfo.stale))
		
		self.sendmsg(sNick, "----- Known user list end -----")
	
	
	def sendmsg(self, to, msg):
		self.PutIRC("PRIVMSG " + to + " :" +msg)
	
	
	def OnLoad(self, args, message): # const CString &sArgsi, CString &sMessage
		sArgs = str(args)
		
		if len(sArgs) == 0:
			return False
		
		for channelArgs in sArgs.split(":"):
			tokens = channelArgs.split()
			
			if len(tokens) < 3 or len(tokens[0]) < 2 or tokens[0][0] != '#' :
				self.PutModule("Ignored because of missing channel or administrator list: " + channelArgs)
			
			if tokens[0] in self.chans:
				self.chans[tokens[0]].activator = tokens[1][0]
				self.chans[tokens[0]].admins = tokens[2:]
			else:
				self.chans[tokens[0]] = ChanInfo(self, tokens[0], tokens[1][0], tokens[2:])
		
		return len(self.chans) > 0
	
	
	def OnIRCConnected(self):
		self.reset()
	
	
	def OnModCommand(self, sCommand): # const CString &sCommand
		self.parseMessage(str(sCommand), console=True)
	
	
	def OnPrivMsg(self, nick, sMessage): # EModRet OnPrivMsg (CNick &Nick, CString &sMessage)
		message = str(sMessage)
		
		self.parseMessage(message, nick)
		
		return znc.HALTCORE
	
	
	def OnChanMsg(self, nick, channel, sMessage): #EModRet OnChanMsg (CNick &Nick, CChan &Channel, CString &sMessage)
		sChan = str(channel.GetName())
		message = str(sMessage)
		
		if sChan in self.chans:
			chan = self.chans[sChan]
			
			if len(message) > 1 and message[0] == chan.activator:
				self.parseMessage(message[1:], nick, channel)
		
		return znc.HALTCORE
	
	
	def OnNick(self, nick, sNewNick, vChans): # OnNick (const CNick &Nick, const CString &sNewNick, const std::vector< CChan * > &vChans)
		oldNick = str(nick.GetNick())
		newNick = str(sNewNick)
		
		if oldNick in self.activeNicks: # only track active users, tracking will be re-enabled if the user talks to us again
			userId = self.activeNicks[oldNick]
			userInfo = self.userdb[userId]
			
			# assert !userInfo.stale
			userInfo.nick = newNick
			del self.activeNicks[oldNick]
			self.activeNicks[newNick] = userId
			
			# search and update entry in global nickdb
			self.nickdb[oldNick].remove(userId)
			self.nickdb[newNick].append(userId)
		
		if oldNick in self.whoisdb:
			whoisData = self.whoisdb[oldNick]
			whoisData.nick = newNick
			del self.whoisdb[oldNick]
			self.whoisdb[newNick] = whoisData
	
	
	# test if user can not be tracked any more and handle as if he quitted in this case
	def OnPart(self, nick, channel, sMessage): # OnPart (const CNick &Nick, CChan &Channel, const CString &sMessage)
		commonChans = znc.VChannels()
		nick.GetCommonChans(commonChans, self.GetNetwork())
		
		if len(commonChans) == 0:
			# nick is stale
			self.OnQuit(nick, sMessage, None) # vChans is not required in case of a quit
	
	
	# same as if the user parted by himself
	def OnKick(self, opNick, sKickedNick, channel, sMessage): # OnKick (const CNick &OpNick, const CString &sKickedNick, CChan &Channel, const CString &sMessage)
		self.OnPart(sKickedNick, channel, sMessage)
	
	
	# mark user as stale and delete him from the active tracking databases
	def OnQuit(self, zNick, sMessage, vChans): # OnQuit (const CNick &Nick, const CString &sMessage, const std::vector< CChan * > &vChans)
		nick = str(zNick.GetNick())
		
		if nick in self.activeNicks:
			userInfo = self.userdb[self.activeNicks[nick]]
			userInfo.stale = True
			
			del self.activeNicks[nick]
		
		if nick in self.whoisdb:
			del self.whoisdb[nick]
	
	
	def OnRaw(self, sLine): # EModRet OnRaw (CString &sLine)
		# lines of interest are structured like this:
		# :SERVER  CMD  OWN_NICK  QUERY_NICK  ARGS
		# <CMD> = three digit code

		tokens = str(sLine).strip().split(None, 4)
		
		if len(tokens) < 5:
			return znc.CONTINUE # do not care
		
		sSrv = self.GetNetwork().GetIRCServer()
		
		if tokens[0][1:] != sSrv:
			return znc.CONTINUE # not our network
		
		RAWCmd = -1
		if len(tokens[1]) == 3 and tokens[1].isdigit():
			RAWCmd = int(tokens[1])
		
		if RAWCmd < 0:
			return znc.CONTINUE # most likely something is wrong with this command, delegate to ZNC
		
		if tokens[3] not in self.whoisdb:
			return znc.CONTINUE # did not request this line
		
		# five-token line, right network and queried nick. consume and do not forward
		
		whoisData = self.whoisdb[tokens[3]]
		
		if RAWCmd == 311:
			# :morgan.freenode.net 311 OWN_NICK QUERY_NICK IDENT HOST * :REALNAME
			args = tokens[4].split()
			
			if len(args) < 4:
				whoisData.error = True
			else:
				whoisData.nick = tokens[3]
				whoisData.ident = args[0]
				whoisData.host = args[1]
		elif RAWCmd == 330:
			# :morgan.freenode.net 330 OWN_NICK QUERY_NICK NICKSERV_USER :is logged in as
			args = tokens[4].split(None, 1)
			
			if len(args) < 2 or args[1] != ":is logged in as":
				whoisData.error = True
			else:
				whoisData.nickuser = args[0]
		elif RAWCmd == 307:
			# :irc.rbx.fr.euirc.net 307 OWN_NICK QUERY_NICK :is a registered nick
			if tokens[4] != ":is a registered nick":
				whoisData.error = True
			else:
				whoisData.nickuser = tokens[3]
		elif RAWCmd == 318:
			# :morgan.freenode.net 318 OWN_NICK QUERY_NICK :End of /WHOIS list.
			listeners = self.whoisCallbacks[tokens[3]]
			del self.whoisCallbacks[tokens[3]]
			
			error = whoisData.error or whoisData.nick is None
			
			if not error:
				whoisData.valid = True
			else:
				del self.whoisdb[tokens[3]]
			
			for callback in listeners:
				callback(tokens[3], error)
		
		return znc.HALTCORE # this line ends here!

