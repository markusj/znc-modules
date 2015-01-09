# timer.py

# a module to invoke IRC commands in a timed manner

import znc

class delay_cmd_timer(znc.Timer):
	def RunJob(self):
		self.GetModule().PutIRC(self.command)

class timer(znc.Module):
	description = "TIMER command, usage: TIMER <network> <seconds> <command>"
	module_types = [ znc.CModInfo.NetworkModule ]
	timer_generation = 0
	
	def OnModCommand(self, sCommand): # const CString & sCommand
		self.OnSendToIRC("timer " + self.GetNetwork().GetName() + " " + str(sCommand))
	
	def OnSendToIRC(self, sLine): # CString & sLine
		parts = str(sLine).partition(" ") # split at first whitespace
		
		if not parts[0].lower() == "timer":
			return znc.CONTINUE # command does not match
		
		parts = parts[2].lstrip().partition(" ") # remove whitespace and continue
		
		argnetwork = parts[0]
		sNetwork = str(self.GetNetwork().GetName())
		sUser = str(self.GetUser().GetUserName())
		
		if not argnetwork == sNetwork.lower():
			return znc.CONTINUE # network does not match
		
		parts = parts[2].lstrip().partition(" ") # remove whitespace and continue
		
		argdelay = parts[0]
		argcmd = parts[2].lstrip()
		
		if not argdelay.isdigit() or len(argcmd) == 0:
			self.PutModule(self.description)
			
			return znc.HALTCORE # do not forward
		
		t = self.CreateTimer(delay_cmd_timer, interval=int(argdelay), label="delay_cmd_timer-" + sUser + "-" + sNetwork + "-" + str(self.timer_generation))
		t.command = argcmd
		
		self.timer_generation += 1
		
		return znc.HALT # do neither forward nor process anywhere else
