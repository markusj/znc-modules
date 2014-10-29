# awaymonitor.py

# a module restore the (auto) away state in case of a disconnect
# multi-client auto-away: send away message "detached". If the last user changed
#                         to away, this state will be forwarded to the network.
#                         Different away messages will be forwarded directly and
#                         override/disable the auto-away mechanism until a client
#                         sets itself as back.

import znc

class awaymonitor(znc.Module):
	description = "Restores client away state in case of a disconnect"
	module_types = [ znc.CModInfo.NetworkModule ]
	has_args = True
	args_help_text = "Away message which will be set if auto-away triggers"
	DETACHED_MSG = "detached"
	# m_bIsAway
	# m_bClientSetAway
	# m_sAwayMsg
	# m_sClientAwayMsg
	
	def __init__(self):
		self.m_bIsAway = False
		self.m_bClientSetAway  = False
		self.m_sAwayMsg = self.DETACHED_MSG
		self.m_sClientAwayMsg = self.DETACHED_MSG # default, will be overwritten later
	
	
	def OnLoad(self, args, message): # const CString &sArgsi, CString &sMessage
		sArgs = str(args)
		
		if len(sArgs) > 0:
			self.m_sAwayMsg = sArgs
		
		self.m_bIsAway = not self.GetNetwork().IsUserOnline()
		self._UpdateAwayState()
		
		return True
	
	
	def OnUserRaw(self, sLine): # CString &sLine
		tokens = str(sLine).split(None, 1)
		
		if (len(tokens) == 0) or (not tokens[0].lower() == "away"):
			return znc.CONTINUE # nothing to do
		
		# parse away command
		if (len(tokens) == 1) or (tokens[1][1:].strip() == ""):
			# user is back
			self.m_bClientSetAway = False
			self.m_bIsAway = False
			self.GetClient().SetAway(False) # track client away state
			
			return znc.CONTINUE # do not intercept command
		# else: len(tokens) > 1 and not empty: got a new away command
		awayArg = tokens[1][1:].strip()
		
		self.GetClient().SetAway(True) # track client away state
		
		if awayArg != self.DETACHED_MSG:
			self.m_bClientSetAway = True # user set himself away, disable auto-away
			self.m_sClientAwayMsg = awayArg
			
			return znc.CONTINUE # do not intercept command
		
		# else: got a "detached away" command, is something to do?
		if not self.m_bClientSetAway:
			self.m_bIsAway = not self.GetNetwork().IsUserOnline()
			self._UpdateAwayState()
		
		return znc.HALTCORE # intercept "detached away"
	
	
	#def OnClientLogin():
		# nothing to do here, job is done by IRCNetwork::ClientConnected()
	
	#def OnClientDisconnect():
		# case is not relevant here
	
	def OnIRCConnected(self):
		self._UpdateAwayState()
	
	
	def _UpdateAwayState(self):
		networkAway = self.GetNetwork().IsIRCAway()
		
		if self.m_bClientSetAway and not networkAway:
			# replay user's away message
			self.PutIRC("AWAY :" + self.m_sClientAwayMsg)
		elif self.m_bIsAway != networkAway:
			# apply auto away state
			if self.m_bIsAway:
				self.PutIRC("AWAY :" + self.m_sAwayMsg)
			else:
				self.PutIRC("AWAY")

