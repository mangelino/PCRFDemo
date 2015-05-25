from PCC import Rule, Session, MonitoringInfo, RulesActions, StaticRule, QoSInfo, FlowInfo, SDFTemplate
import PCC
import requests
import json
from collections import namedtuple
from datetime import datetime

Message = namedtuple("Message", "name type subtype fr to time content")

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
		self.messages = []
		# For the moment we leave the rules hardcoded
		self.staticRule = {}

		self.staticRule["Data"] = StaticRule(name="Data", chargingId=1, 
			qosInfo=QoSInfo("Data", 6, 1000, 10000, 10000, 1000,0),
			flowInfo = FlowInfo([
				SDFTemplate("default","255","*.*.*.*","all","*.*.*.*","all","all")
			]),
			monitoringKey = "Data",
			sponsorId = None,
			precedence = 255)

		self.staticRule["Throttle"] = StaticRule(name="Throttle", chargingId=1, 
			qosInfo=QoSInfo("Throttle", 6, 1000, 1000, 2000, 50,0),
			flowInfo = FlowInfo([
				SDFTemplate("default","255","*.*.*.*","all","*.*.*.*","all","all")
			]),
			monitoringKey = "Data",
			sponsorId = None,
			precedence = 50)

		self.staticRule["Throttle_Group"] = StaticRule(name="Throttle_Group", chargingId=1, 
			qosInfo=QoSInfo("Throttle_Group", 6, 1000, 1000, 2000, 20,0),
			flowInfo = FlowInfo([
				SDFTemplate("default","255","*.*.*.*","all","*.*.*.*","all","all")
			]),
			monitoringKey = "Data",
			sponsorId = None,
			precedence = 40)

		self.staticRule["Youtube"] = StaticRule(name="Youtube", chargingId=1, 
			qosInfo=QoSInfo("Youtube", 5, 1000, 1000, 2000, 2000,0),
			flowInfo = FlowInfo([
				SDFTemplate("youtube","100","youtube.com","all","*.*.*.*","all","all")
			]),
			monitoringKey = "Youtube",
			sponsorId = None,
			precedence = 30)

		self.staticRule["SportVod"] = StaticRule(name="SportVod", chargingId=1, 
			qosInfo=QoSInfo("Livevideo", 4, 1000, 1000, 2000, 2000,0),
			flowInfo = FlowInfo([
				SDFTemplate("sportvod","90","sport.cdn.starmobile.com","all","*.*.*.*","all","all")
			]),
			monitoringKey = "SportVod",
			sponsorId = None,
			precedence = 20)

		self.staticRule["Turbo"] = StaticRule(name="Turbo", chargingId=1, 
			qosInfo=QoSInfo("Turbo", 6, 1000, 1000, 2000, 2000,0),
			flowInfo = FlowInfo([
				SDFTemplate("default","255","*.*.*.*","all","*.*.*.*","all","all")
			]),
			monitoringKey = "Data",
			sponsorId = None,
			precedence = 35)

		self.rules["Data"] = Rule("Data", 6, 1000, 10000, 10000, 1000)
		self.rules["Throttle"] = Rule("Throttle", 6, 1000, 1000, 2000, 50)
		self.rules["Data_Group"] = Rule("Data_Group", 6, 1000, 10000, 10000, 1000)
		self.rules["Throttle_Group"] = Rule("Throttle_Group", 6, 1000, 1000, 2000, 20)
		self.rules["Youtube"] = Rule("Youtube", 6, 1000, 1000, 2000, 2000)
		self.rules["Turbo"] = Rule("Youtube", 6, 1000, 1000, 2000, 2000)

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
		ccr_cycle_list = json.loads(simulator_ans)
		session = None
		code = PCC.DIAMETER_SUCCESS
		for ccr_cycle in ccr_cycle_list:
			if "Answer" in ccr_cycle and ccr_cycle["Answer"] != None:
				ccr_ans = ccr_cycle["Answer"]
				self.messages.append(Message("CC", "R", ccr_cycle["Request"]["CC_Request_Type"],"PCEF", "PCRF", datetime.now(), ccr_cycle_list[0]["Request"]))
				self.messages.append(Message("CC", "A", ccr_ans["CC_Request_Type"],"PCRF", "PCEF", datetime.now(), ccr_ans))
				rules = RulesActions()
				code = ccr_ans["Result_Code"]
				if ccr_ans["Result_Code"] == PCC.DIAMETER_SUCCESS:
					session_id = ccr_ans["Session_Id"]
					atHome = self.users[identity].isAtHome
					session = Session(identity, session_id, {}, set(), atHome)
					self.sessions[session_id] = session
					self.users[identity].sessions.append(session)
					print "Sessions:",self.users[identity].sessions
					json_pretty = json.dumps(ccr_ans, sort_keys = True, indent = 4, separators = (', ', ': '))
					print "CCR Answer = ",json_pretty
					
					checkUsageMonitoringInfo(ccr_ans, session)
					rules = checkChargingRuleName(ccr_ans)
					updateSession(session, rules)
			else:
				self.messages.append(Message("RA", "R", ccr_cycle["Request"]["Re_Auth_Request_Type"],"PCRF", "PCEF", datetime.now(), ccr_cycle_list[0]["Request"]))
				

		return (code, session, rules.asDict())

	def terminateUESession(self,sessionid):
		
		session = self.sessions[sessionid]
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
		ccr_cycle_list = json.loads(simulator_ans)
		code = PCC.DIAMETER_SUCCESS		
		for ccr_cycle in ccr_cycle_list:
			if "Answer" in ccr_cycle and ccr_cycle["Answer"] != None:
				ccr_ans = ccr_cycle["Answer"]

				self.messages.append(Message("CC", "R", ccr_cycle["Request"]["CC_Request_Type"], "PCEF", "PCRF", datetime.now(), ccr_cycle["Request"]))
				self.messages.append(Message("CC", "A", ccr_ans["CC_Request_Type"],"PCRF", "PCEF", datetime.now(), ccr_ans))
				code = ccr_ans["Result_Code"]
				if ccr_ans["Result_Code"] == PCC.DIAMETER_SUCCESS:
					session_id = ccr_ans["Session_Id"]
					
					self.users[identity].sessions.pop(self.users[identity].sessions.index(session))
					self.sessions.pop(sessionid)

					json_pretty = json.dumps(ccr_ans, sort_keys = True, indent = 4, separators = (', ', ': '))
					print "CCR_Answer=", json_pretty

					checkUsageMonitoringInfo(ccr_ans, session)
					#checkChargingRuleName(ccr_ans, session)
			else:
				self.messages.append(Message("RA", "R", ccr_cycle["Request"]["Re_Auth_Request_Type"], "PCRF", "PCEF", datetime.now(), ccr_cycle["Request"]))
				

		return code

	def reportSessionUsage(self, sessionid, request):
		session = self.sessions[sessionid]
		identity = session.identity
		atHome = int(request.form["isAtHome"])
		print session, atHome
		if atHome != session.atHomeLocation:
			self.sessions[sessionid] = session._replace(atHomeLocation = atHome)
			session = self.sessions[sessionid]
		print session
		#Update the usage for each key
		simQuery={"action":"Update"}
		simQuery["sessionid"] = session.sessionId
		simQuery["isAtHome"] = session.atHomeLocation
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
		ccr_cycle_list = json.loads(simulator_ans)
		rules = RulesActions()
		result_code = PCC.DIAMETER_SUCCESS

		for ccr_cycle in ccr_cycle_list:

			if "Answer" in ccr_cycle and ccr_cycle["Answer"] != None:

				ccr_ans = ccr_cycle["Answer"]
				self.messages.append(Message("CC", "R", ccr_cycle["Request"]["CC_Request_Type"], "PCEF", "PCRF", datetime.now(), ccr_cycle["Request"]))
				self.messages.append(Message("CC", "A", ccr_ans["CC_Request_Type"], "PCRF", "PCEF", datetime.now(), ccr_ans))
				session_id = ccr_ans["Session_Id"]
				
				json_pretty = json.dumps(ccr_ans, sort_keys = True, indent = 4, separators = (', ', ': '))
				print "RA=", json_pretty
				result_code = ccr_ans["Result_Code"] 
				if result_code == PCC.DIAMETER_SUCCESS:
				
					checkUsageMonitoringInfo(ccr_ans, session)
					rules.merge(checkChargingRuleName(ccr_ans))
			else:
				# If the answer is nothing, then this is a RAR message, hence the info is in the request
				ccr_req = ccr_cycle["Request"]
				self.messages.append(Message("RA", "R", ccr_cycle["Request"]["Re_Auth_Request_Type"], "PCRF", "PCEF", datetime.now(), ccr_cycle["Request"]))
				session_id = ccr_req["Session_Id"]
			
				json_pretty = json.dumps(ccr_req, sort_keys = True, indent = 4, separators = (', ', ': '))
				print "RAR=", json_pretty
				rules.merge(checkChargingRuleName(ccr_req))

		updateSession(session, rules)

		return (result_code, rules.asDict())

	def simEndPoint(self):
		return self.diameterIP+':'+self.diameterPort+'/'

def updateSession(session, rules):
	# Update installed sessions rules
	for rule in rules.install:
		session.installedRules.add(rule)
	for rule in rules.remove:
		session.installedRules.discard(rule)

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

def checkChargingRuleName(ccr_ans):

	rules = RulesActions()
	if "Charging_Rule_Install" in ccr_ans:
		for chargingRule in ccr_ans["Charging_Rule_Install"]:
			for chargingRuleName in chargingRule["Charging_Rule_Name"]:
				#session.installedRules.append(baToStr(chargingRuleName))
				rules.installRule(baToStr(chargingRuleName))
	if "Charging_Rule_Remove" in ccr_ans:
		for chargingRule in ccr_ans["Charging_Rule_Remove"]:
			for chargingRuleName in chargingRule["Charging_Rule_Name"]:
					#index = session.installedRules.index(baToStr(chargingRuleName))
				rules.removeRule(baToStr(chargingRuleName))
					#session.installedRules.pop(index)
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
