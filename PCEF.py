from PCC import Rule, Session, MonitoringInfo
import PCC
import requests
import json

class PCEF:
	def __init__(self, pcefid, name, ip, port):
		#users.clear()
		self.id = pcefid
		self.name = name
		self.diameterIP = ip
		self.diameterPort = port
		self.users = {}
		self.sessions = {}
		self.rules = {}
		# For the moment we leave the rules hardcoded
		self.rules["Data"] = Rule("Data", 6, 1000, 10000, 10000, 50000)
		self.rules["Throttle"] = Rule("Throttle", 6, 1000, 1000, 2000, 2000)
		self.rules["Data_Group"] = Rule("Data_Group", 6, 1000, 10000, 10000, 50000)
		self.rules["Throttle_Group"] = Rule("Throttle_Group", 6, 1000, 1000, 2000, 2000)
		self.rules["Youtube"] = Rule("Youtube", 6, 1000, 1000, 2000, 2000)

	def resetPCEF(self):
		self.users.clear()
		self.sessions.clear()

	def registerUE(self, UE):
		self.users[UE.identity] = UE
		UE.assignPCEF(self)

	def forwardQuery(self, type, identity):
		simQuery = {}
		simQuery = {"action":type}
		ue = self.users[identity]._asdict()
		
		simQuery.update(ue)
		simQuery["rat"] = 1000 #request.args["rat"]
		simQuery["calledStationId"] = "mc@mo.com" #request.args["calledStationId"]
		print simQuery
		return requests.get(self.simEndPoint(),params=simQuery)

	def createUESession(self, identity):
		r = self.forwardQuery("Start", identity)
	
		simulator_ans = r.content
		ccr_cycle = json.loads(simulator_ans)
		
		ccr_ans = ccr_cycle["Answer"]
		rules = None
		if ccr_ans["Result_Code"] == PCC.DIAMETER_SUCCESS:
			session_id = ccr_ans["Session_Id"]
			session = Session(identity, session_id, {}, [])
			self.sessions[session_id] = session
			self.users[identity].sessions.append(session)
			print "Sessions:",self.users[identity].sessions
			json_pretty = json.dumps(ccr_ans, sort_keys = True, indent = 4, separators = (', ', ': '))
			print "CCR Answer = ",json_pretty
			
			checkUsageMonitoringInfo(ccr_ans, session)
			rules = checkChargingRuleName(ccr_ans, session)

		return (ccr_ans["Result_Code"], rules)

	def terminateUESession(self,sessionid):
		
		session = sessions[sessionid]
		identity = session.identity
		#return "Deleted"
		#Update the usage for each key
		simQuery={"action":"Stop"}
		simQuery["sessionid"] = session.sessionId;
		
		print simQuery
		
		ue = self.users[identity]._asdict()
		
		print ue
		simQuery.update(ue)
		#TODO: These parameters should be stored in the sessions object
		simQuery["rat"] = 1000 #request.args["rat"]
		simQuery["calledStationId"] = "mc@mo.com" #request.args["calledStationId"]
		
		print simQuery
		r = requests.get(self.simEndPoint(),params=simQuery)
	 	simulator_ans = r.content
		ccr_cycle = json.loads(simulator_ans)
		

		ccr_ans = ccr_cycle["Answer"]
		if ccr_ans["Result_Code"] == PCC.DIAMETER_SUCCESS:
			session_id = ccr_ans["Session_Id"]
			
			self.users[identity].sessions.pop(users[identity].sessions.index(session))
			self.sessions.pop(sessionid)

			json_pretty = json.dumps(ccr_ans, sort_keys = True, indent = 4, separators = (', ', ': '))
			print "CCR_Answer=", json_pretty

			checkUsageMonitoringInfo(ccr_ans, session)
			#checkChargingRuleName(ccr_ans, session)
			return True
		return False

	def reportSessionUsage(self, sessionid, request):
		session = self.sessions[sessionid]
		identity = session.identity
		#Update the usage for each key
		simQuery={"action":"Update"}
		simQuery["sessionid"] = session.sessionId
		print request.form
		for minfo in session.monitoringInfo.values():
			print "minfo", minfo
			if minfo.key in request.form:
				if request.form[minfo.key].isdigit():
					newUsage = int(request.form[minfo.key])
					simQuery["mk"+str(minfo.intKey)+"Name"] = minfo.key
					simQuery["mk"+str(minfo.intKey)+"Value"]= newUsage
					# It is ok, since I can consume data even in the PCRF does not respond
					# Should enforce that only the granted data is allowed before requesting new
					session.monitoringInfo[minfo.key] = minfo._replace(usage = minfo.usage+newUsage)
					print "minfo=", session.monitoringInfo[minfo.key]
		
		print simQuery
		
		ue = self.users[identity]._asdict()
		
		print ue
		simQuery.update(ue)
		#TODO: These parameters should be stored in the sessions object
		simQuery["rat"] = 1000 #request.args["rat"]
		simQuery["calledStationId"] = "mc@mo.com" #request.args["calledStationId"]
		
		print simQuery
		r = requests.get(self.simEndPoint(),params=simQuery)
	 	simulator_ans = r.content
		ccr_cycle = json.loads(simulator_ans)
		

		ccr_ans = ccr_cycle["Answer"]
		session_id = ccr_ans["Session_Id"]
		
		json_pretty = json.dumps(ccr_ans, sort_keys = True, indent = 4, separators = (', ', ': '))
		print "CCR_Answer=", json_pretty
		rules = None
		if ccr_ans["Result_Code"] == PCC.DIAMETER_SUCCESS:
		
			checkUsageMonitoringInfo(ccr_ans, session)
			rules = checkChargingRuleName(ccr_ans, session)

		return (int(ccr_ans["Result_Code"]), rules)

	def simEndPoint(self):
		return self.diameterIP+':'+self.diameterPort+'/'


def checkUsageMonitoringInfo(ccr_ans, session):
	if "Usage_Monitoring_Information"  in ccr_ans:
		for monitoring_info in ccr_ans["Usage_Monitoring_Information"]:
			print ("MonInfo: " + str(monitoring_info))
			mkey = baToStr(monitoring_info["Monitoring_Key"])
			if not mkey in session.monitoringInfo:
				session.monitoringInfo[mkey] = MonitoringInfo(mkey, len(session.monitoringInfo), "", 0,0,0)
				#keysToAdd.append(session.monitoringInfo[mkey])
			minfo = session.monitoringInfo[mkey]
			
			session.monitoringInfo[mkey] = minfo._replace(gsu = monitoring_info['Granted_Service_Unit'][0]['CC_Total_Octets'])
			print "minfo=", session.monitoringInfo[mkey]

def checkChargingRuleName(ccr_ans, session):

	rules = {"install":[], "remove":[]}
	if "Charging_Rule_Install" in ccr_ans:
		for chargingRule in ccr_ans["Charging_Rule_Install"]:
			for chargingRuleName in chargingRule["Charging_Rule_Name"]:
				session.installedRules.append(baToStr(chargingRuleName))
				rules["install"].append(baToStr(chargingRuleName))
	if "Charging_Rule_Remove" in ccr_ans:
		for chargingRule in ccr_ans["Charging_Rule_Remove"]:
			for chargingRuleName in chargingRule["Charging_Rule_Name"]:
				if baToStr(chargingRuleName) in session.installedRules:
					index = session.installedRules.index(baToStr(chargingRuleName))
					rules["remove"].append(baToStr(chargingRuleName))
					session.installedRules.pop(index)
	return rules


def baToStr(byteArray):
	return "".join([chr(c) for c in byteArray])

def printSessions(sessions):
	print "Sessions"
	for sessions in pcef_sessions.values():
		for s in sessions:
			print s.identity, s.monitoringInfo
			for minfo  in s.monitoringInfo.values():
				print minfo.key, minfo.gsu, minfo.usage