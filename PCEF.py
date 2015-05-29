from PCC import Rule, Session, MonitoringInfo, RulesActions, StaticRule, QoSInfo, FlowInfo, SDFTemplate
import PCC
import requests
import json
from collections import namedtuple
from datetime import datetime


Message = namedtuple("Message", "name type subtype fr to time content descr")

def prettyPrintJson(title, jsonobj):
    print title, "=" , json.dumps(jsonobj, sort_keys=True, indent=4, separators= (', ', ': '))

class PCEF:
    def __init__(self, pcefid, name, ip, port):
        #users.clear()
        self.id = pcefid
        self.name = name
        self.diameterIP = ip
        self.diameterPort = port
        self.users = {}
        self.sessions = {}
        #self.rules = {}
        self.messages = []
        # For the moment we leave the rules hardcoded
        self.staticRules = {}

        self.staticRules["Data"] = StaticRule(name="Data", chargingId=1, 
            qosInfo=QoSInfo("Data", 6, 1000000, 1000000, 1000000, 1000000,0),
            flowInfo = FlowInfo([
                SDFTemplate("default","255","*.*.*.*","all","*.*.*.*","all","all")
            ]),
            monitoringKey = 1,
            sponsorId = None,
            precedence = 255)

        self.staticRules["Throttle"] = StaticRule(name="Throttle", chargingId=1, 
            qosInfo=QoSInfo("Throttle", 6, 100000, 100000, 100000, 100000,0),
            flowInfo = FlowInfo([
                SDFTemplate("default","255","*.*.*.*","all","*.*.*.*","all","all")
            ]),
            monitoringKey = 1,
            sponsorId = None,
            precedence = 50)

        self.staticRules["Throttle_Group"] = StaticRule(name="Throttle_Group", chargingId=1, 
            qosInfo=QoSInfo("Throttle_Group", 6, 50000, 50000, 50000, 50000,0),
            flowInfo = FlowInfo([
                SDFTemplate("default","255","*.*.*.*","all","*.*.*.*","all","all")
            ]),
            monitoringKey = 1,
            sponsorId = None,
            precedence = 40)

        self.staticRules["Youtube"] = StaticRule(name="Youtube", chargingId=1, 
            qosInfo=QoSInfo("Youtube", 5, 1000000, 1000000, 2000000, 2000000, 0),
            flowInfo = FlowInfo([
                SDFTemplate("youtube","100","youtube.com","all","*.*.*.*","all","all")
            ]),
            monitoringKey = 2,
            sponsorId = None,
            precedence = 30)

        self.staticRules["SportVod"] = StaticRule(name="SportVod", chargingId=1, 
            qosInfo=QoSInfo("Livevideo", 4, 1000000, 1000000, 2000000, 2000000, 0),
            flowInfo = FlowInfo([
                SDFTemplate("sportvod","90","sport.cdn.starmobile.com","all","*.*.*.*","all","all")
            ]),
            monitoringKey = 3,
            sponsorId = None,
            precedence = 20)

        self.staticRules["Turbo"] = StaticRule(name="Turbo", chargingId=1, 
            qosInfo=QoSInfo("Turbo", 6, 1000000, 1000000, 2000000, 2000000,0),
            flowInfo = FlowInfo([
                SDFTemplate("default","255","*.*.*.*","all","*.*.*.*","all","all")
            ]),
            monitoringKey = 1,
            sponsorId = None,
            precedence = 35)

    def resetPCEF(self):
        self.users.clear()
        self.sessions.clear()

    def registerUE(self, UE):
        self.users[UE.identity] = UE
        UE.assignPCEF(self)

    def createBaseQuery(self, action, identity, sessionid=None):
        simQuery = {}
        simQuery = {"action":action}
        ue = self.users[identity]._asdict()
        if sessionid != None:
            simQuery["sessionid"] = sessionid
        simQuery.update(ue)
        simQuery["rat"] = 1000 #request.args["rat"]
        simQuery["calledStationId"] = "mc@mo.com" #request.args["calledStationId"]
        return simQuery
        return requests.get(self.simEndPoint(),params=simQuery)

    def processCCMessages(self, ccr_cycle_list, cca_success, cca_failure, rar_request):
        ### TODO: refactor the processing of the CCR list answers to avoid repeating the code
        pass

    def createUESession(self, identity):
        simQuery = self.createBaseQuery(action="Start", identity=identity)
        self.__firstUpdate = True
        r = requests.get(self.simEndPoint(),params=simQuery)
        simulator_ans = r.content
        ccr_cycle_list = json.loads(simulator_ans)
        session = None
        code = PCC.DIAMETER_SUCCESS
        for ccr_cycle in ccr_cycle_list:
            if "Answer" in ccr_cycle and ccr_cycle["Answer"] != None:
                ccr_ans = ccr_cycle["Answer"]
                rules = RulesActions()
                code = ccr_ans["Result_Code"]
                if ccr_ans["Result_Code"] == PCC.DIAMETER_SUCCESS:
                    session_id = ccr_ans["Session_Id"]
                    atHome = self.users[identity].isAtHome
                    # Create a new session object and store it
                    session = Session(identity, session_id, {}, set(), atHome, None)
                    self.sessions[session_id] = session
                    self.users[identity].sessions.append(session)
                    #print "Sessions:",self.users[identity].sessions
                    
                    checkUsageMonitoringInfo(ccr_ans, session)
                    rules = checkChargingRuleName(ccr_ans)
                    checkQoSInfo(ccr_ans, session)

                    if len(rules.install)+len(rules.remove) > 0 or "QoS_Information" in ccr_ans:
                        self.messages.append(Message("CC", "R", ccr_cycle["Request"]["CC_Request_Type"],"PCEF", "PCRF", datetime.now(), ccr_cycle_list[0]["Request"], "usage report"))
                        descr = "+"+",".join(rules.install)+"/-"+",".join(rules.remove)
                        if "QoS_Information" in ccr_ans:
                            descr+="/qos"
                        self.messages.append(Message("CC", "A", ccr_ans["CC_Request_Type"],"PCRF", "PCEF", datetime.now(), ccr_ans, descr))
                        prettyPrintJson("CCA", ccr_ans)
        
                    updateSession(session, rules)
                else:
                    prettyPrintJson("CCA", ccr_ans)
                    self.messages.append(Message("CC", "R", ccr_cycle["Request"]["CC_Request_Type"],"PCEF", "PCRF", datetime.now(), ccr_cycle_list[0]["Request"], ""))
                    self.messages.append(Message("CC", "A", "","PCRF", "PCEF", datetime.now(), ccr_ans, ""))
                    print "CCR Answer = ",json.dumps(ccr_ans, sort_keys = True, indent = 4, separators = (', ', ': '))
            else:
                prettyPrintJson("RAR", ccr_cycle["Request"]) 
                self.messages.append(Message("RA", "R", ccr_cycle["Request"]["Re_Auth_Request_Type"],"PCRF", "PCEF", datetime.now(), ccr_cycle_list[0]["Request"], ""))
                
        return (code, session, rules.asDict())

    def terminateUESession(self,sessionid):
        
        session = self.sessions[sessionid]
        identity = session.identity
        
        simQuery = self.createBaseQuery(action="Stop", identity=identity, sessionid = sessionid)        
        r = requests.get(self.simEndPoint(),params=simQuery)
        simulator_ans = r.content

        ccr_cycle_list = json.loads(simulator_ans)
        code = PCC.DIAMETER_SUCCESS     
        for ccr_cycle in ccr_cycle_list:

            if "Answer" in ccr_cycle and ccr_cycle["Answer"] != None:
                ccr_ans = ccr_cycle["Answer"]
                self.messages.append(Message("CC", "R", ccr_cycle["Request"]["CC_Request_Type"], "PCEF", "PCRF", datetime.now(), ccr_cycle["Request"], "terminate"))
                self.messages.append(Message("CC", "A", ccr_ans["CC_Request_Type"],"PCRF", "PCEF", datetime.now(), ccr_ans, ""))

                code = ccr_ans["Result_Code"]
                if ccr_ans["Result_Code"] == PCC.DIAMETER_SUCCESS:
                    session_id = ccr_ans["Session_Id"]
                    
                    self.users[identity].sessions.pop(self.users[identity].sessions.index(session))
                    self.sessions.pop(sessionid)
                    prettyPrintJson(CCA, ccr_ans)
                    
                    checkUsageMonitoringInfo(ccr_ans, session)
                    #checkChargingRuleName(ccr_ans, session)
            else:
                prettyPrintJson("RAR", ccr_cycle["Request"])
                self.messages.append(Message("RA", "R", ccr_cycle["Request"]["Re_Auth_Request_Type"], "PCRF", "PCEF", datetime.now(), ccr_cycle["Request"], ""))

        return code


    def reportSessionUsage(self, sessionid, request):
        session = self.sessions[sessionid]
        identity = session.identity
        atHome = int(request.form["isAtHome"])
        #print "Session",session, "AtHome:", atHome
        if atHome != session.atHomeLocation:
            self.sessions[sessionid].atHomeLocation = atHome
            session = self.sessions[sessionid]

        #Create the base query 
        simQuery = self.createBaseQuery(action="Update", identity=identity, sessionid=sessionid)
        
        simQuery["isAtHome"] = session.atHomeLocation
        # Add the usage keys and values to the query
        for minfo in session.monitoringInfo.values():
            #print "minfo", minfo
            if minfo.key in request.form:
                if request.form[minfo.key].isdigit():
                    newUsage = int(request.form[minfo.key])
                    simQuery["mk"+str(minfo.intKey)+"Name"] = minfo.key
                    simQuery["mk"+str(minfo.intKey)+"Value"]= newUsage
                    # It is ok, since I can consume data even in the PCRF does not respond
                    # Should enforce that only the granted data is allowed before requesting new
                    session.monitoringInfo[minfo.key] = minfo._replace(usage = minfo.usage+newUsage)
                    print "minfo=", session.monitoringInfo[minfo.key]
                
        #print "Query:",simQuery
        r = requests.get(self.simEndPoint(),params=simQuery)
        simulator_ans = r.content
        ccr_cycle_list = json.loads(simulator_ans)
        rules = RulesActions()
        result_code = PCC.DIAMETER_SUCCESS

        for ccr_cycle in ccr_cycle_list:

            if "Answer" in ccr_cycle and ccr_cycle["Answer"] != None:

                ccr_ans = ccr_cycle["Answer"]
                session_id = ccr_ans["Session_Id"]
                                
                result_code = ccr_ans["Result_Code"] 
                if result_code == PCC.DIAMETER_SUCCESS:
                
                    checkUsageMonitoringInfo(ccr_ans, session)
                    checkQoSInfo(ccr_ans, session)
                    newRules = checkChargingRuleName(ccr_ans)
                    rules.merge(newRules)
                    if len(rules.install)+len(rules.remove) > 0 or "QoS_Information" in ccr_ans or self.__firstUpdate:
                        prettyPrintJson("RAR", ccr_ans)

                        self.__firstUpdate = not self.__firstUpdate
                        descr = "+"+",".join(rules.install)+"/-"+",".join(rules.remove)
                        if "QoS_Information" in ccr_ans:
                            descr+="/qos"
                        self.messages.append(Message("CC", "R", ccr_cycle["Request"]["CC_Request_Type"], "PCEF", "PCRF", datetime.now(), ccr_cycle["Request"], "usage report"))
                        self.messages.append(Message("CC", "A", ccr_ans["CC_Request_Type"], "PCRF", "PCEF", datetime.now(), ccr_ans, descr))
                
            else:
                # If the answer is nothing, then this is a RAR message, hence the info is in the request
                ccr_req = ccr_cycle["Request"]
                
                session_id = ccr_req["Session_Id"]
            
                prettyPrintJson("RAR", ccr_req)
                
                rules.merge(checkChargingRuleName(ccr_req))
                checkQoSInfo(ccr_req, session)
                descr = "+"+",".join(rules.install)+"/-"+",".join(rules.remove)
                if "QoS_Information" in ccr_req:
                    descr+="/qos"
                self.messages.append(Message("RA", "R", ccr_cycle["Request"]["Re_Auth_Request_Type"], "PCRF", "PCEF", datetime.now(), ccr_cycle["Request"], descr))

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
            #print ("MonInfo: " + str(monitoring_info))
            mkey = baToStr(monitoring_info["Monitoring_Key"])
            if not mkey in session.monitoringInfo:
                session.monitoringInfo[mkey] = MonitoringInfo(mkey, len(session.monitoringInfo), "", 0,0,0)
                #keysToAdd.append(session.monitoringInfo[mkey])
            minfo = session.monitoringInfo[mkey]
            
            session.monitoringInfo[mkey] = minfo._replace(gsu = monitoring_info['Granted_Service_Unit'][0]['CC_Total_Octets'])
            #print "minfo=", session.monitoringInfo[mkey]

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

def checkQoSInfo(ccr_ans, session):
    mbr_ul = 9999999
    mbr_dl = 9999999
    gbr_ul = 9999999
    gbr_dl = 9999999
    qci = 0
    if "QoS_Information" in ccr_ans:
        for qosInfo in ccr_ans["QoS_Information"]:
            mbr_ul = min(mbr_ul, qosInfo["Max_Requested_Bandwidth_UL"]);
            mbr_dl = min(mbr_dl, qosInfo["Max_Requested_Bandwidth_DL"]);
            gbr_ul = min(gbr_ul, qosInfo["Guaranteed_Bitrate_UL"]);
            gbr_dl = min(gbr_dl, qosInfo["Guaranteed_Bitrate_DL"]);
            qci = max(qci, qosInfo["QoS_Class_Identifier"]);
        session.qosInfo = QoSInfo(name = "fromPCRF", MBR_UL = mbr_ul, MBR_DL = mbr_dl, GBR_UL = gbr_ul, GBR_DL = gbr_dl, qci = qci, ARP=0)
    # If no QoS info is present, do not do anything. Whatever was set previously is kept

def baToStr(byteArray):
    return "".join([chr(c) for c in byteArray])

def printSessions(sessions):
    print "Sessions"
    for sessions in pcef_sessions.values():
        for s in sessions:
            print s.identity, s.monitoringInfo
            for minfo  in s.monitoringInfo.values():
                print minfo.key, minfo.gsu, minfo.usage
