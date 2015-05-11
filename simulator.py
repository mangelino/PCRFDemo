from flask import Flask
from flask import render_template
import flask
from flask import abort
from flask import request
import requests
import json
import jinja2
from collections import namedtuple
from pysimplesoap.client import SoapClient

app = Flask(__name__)

MZ_ROOT = "http://192.168.56.101"
PCEF_PORT = {1:"12008", 2:"12009"}

MonitoringInfo = namedtuple("MonitoringInfo", "key intKey productName gsu usu usage")
Session = namedtuple("UserPolicy", "identity sessionId monitoringInfo installedRules")
UE = namedtuple("UE", "identity identityType userEquipment userEquipmentType sessions pcef")
#users = {}
pcef_users = {1:{}, 2:{}}
pcef_sessions = {1:{}, 2:{}}
all_users = {}
#sessions = {}
Rule = namedtuple("Rule", "name qos uploadMin_kbs downloadMin_kbs uploadMax_kbs downloadMax_kbs")
rules = {}
DiameterError = namedtuple("DiamaterError", "id code description")
diameterErrors = {}
allowed_actions = ["Start", "Stop", "Update", "Refresh", "Reset"]

#req = "D_CC_Request=[Session-Id=172021001178ggsn4.ggsn.com;1430312453633;0123456789101112131415, Auth-Application-Id=4, Origin-Host=sim-gx, Origin-Realm=digitalroute.com, Destination-Realm=digitalroute.com, CC-Request-Type=2, CC-Request-Number=9, Destination-Host=pcrf, Origin-State-Id=0, Subscription-Id=[D_Subscription_Id_AVP=[Subscription-Id-Type=1, Subscription-Id-Data=460004]], Supported-Features=null, TDF-Information=null, Network-Request-Support=0, Packet-Filter-Information=null, Packet-Filter-Operation=0, Bearer-Identifier=null, Bearer-Operation=0, Framed-IP-Address=null, Framed-IPv6-Prefix=null, IP-CAN-Type=0, 3GPP-RAT-Type=0, RAT-Type=1000, Termination-Cause=0, User-Equipment-Info=D_User_Equipment_Info_AVP=[User-Equipment-Info-Type=0, User-Equipment-Info-Value=[B@204b1274], QoS-Information=null, QoS-Negotiation=0, QoS-Upgrade=0, Default-EPS-Bearer-QoS=null, AN-GW-Address=null, 3GPP-SGSN-MCC-MNC=null, 3GPP-SGSN-Address=null, 3GPP-SGSN-IPv6-Address=null, 3GPP-GGSN-Address=null, 3GPP-GGSN-IPv6-Address=null, RAI=null, 3GPP-User-Location-Info=null, 3GPP-MS-TimeZone=null, Called-Station-Id=mc@do.com, PDN-Connection-ID=null, Bearer-Usage=0, Online=0, Offline=0, TFT-Packet-Filter-Information=null, Charging-Rule-Report=null, ADC-Rule-Report=null, Application-Detection-Information=null, Event-Trigger=null, Event-Report-Indication=null, Access-Network-Charging-Address=null, Access-Network-Charging-Identifier-Gx=null, CoA-Information=null, Usage-Monitoring-Information=[D_Usage_Monitoring_Information_AVP=[Monitoring-Key=[B@6a392115, Granted-Service-Unit=null, Used-Service-Unit=[D_Used_Service_Unit_AVP=[Tariff-Change-Usage=0, CC-Time=0, CC-Total-Octets=12000, CC-Input-Octets=0, CC-Output-Octets=0]], Usage-Monitoring-Level=0, Usage-Monitoring-Report=0, Usage-Monitoring-Support=0, AVP=null], D_Usage_Monitoring_Information_AVP=[Monitoring-Key=[B@239e5379, Granted-Service-Unit=null, Used-Service-Unit=[D_Used_Service_Unit_AVP=[Tariff-Change-Usage=0, CC-Time=0, CC-Total-Octets=0, CC-Input-Octets=0, CC-Output-Octets=0]], Usage-Monitoring-Level=0, Usage-Monitoring-Report=0, Usage-Monitoring-Support=0, AVP=null]], Routing-Rule-Install=null, Routing-Rule-Remove=null, Logical-Access-ID=null, Physical-Access-ID=null, Proxy-Info=null, Route-Record=null, AVP=null]"
#ans = "D_CC_Answer=[Session-Id=172021001178ggsn4.ggsn.com;1430312453633;0123456789101112131415, Auth-Application-Id=4, Origin-Host=pcrf, Origin-Realm=digitalroute.com, CC-Request-Type=2, CC-Request-Number=9, Result-Code=2001, Experimental-Result=null, Supported-Features=null, Bearer-Control-Mode=0, Event-Trigger=[5, 13, 33], Origin-State-Id=0, Redirect-Host=null, Redirect-Host-Usage=0, Redirect-Max-Cache-Time=0, Charging-Rule-Remove=null, Charging-Rule-Install=null, ADC-Rule-Remove=null, ADC-Rule-Install=null, Charging-Information=null, Online=0, Offline=0, QoS-Information=null, Revalidation-Time=null, ADC-Revalidation-Time=null, Default-EPS-Bearer-QoS=null, Bearer-Usage=0, 3GPP-User-Location-Info=null, Usage-Monitoring-Information=[D_Usage_Monitoring_Information_AVP=[Monitoring-Key=[B@6b880835, Granted-Service-Unit=[D_Granted_Service_Unit_AVP=[CC-Time=0, CC-Total-Octets=4096, CC-Input-Octets=0, CC-Output-Octets=0, Monitoring-Time=null]], Used-Service-Unit=null, Usage-Monitoring-Level=0, Usage-Monitoring-Report=0, Usage-Monitoring-Support=0, AVP=null], D_Usage_Monitoring_Information_AVP=[Monitoring-Key=[B@277295db, Granted-Service-Unit=[D_Granted_Service_Unit_AVP=[CC-Time=0, CC-Total-Octets=4096, CC-Input-Octets=0, CC-Output-Octets=0, Monitoring-Time=null]], Used-Service-Unit=null, Usage-Monitoring-Level=0, Usage-Monitoring-Report=0, Usage-Monitoring-Support=0, AVP=null]], CSG-Information-Reporting=null, User-CSG-Information=null, Error-Message=null, Error-Reporting-Host=null, Failed-AVP=null, Proxy-Info=null, Route-Record=null, AVP=null]"

def initialize():
	#users.clear()
	users = {}
	all_users.clear()
	users["460001"] = UE("460001", "IMSI", "Samsung Galaxy S4", "IMEISV", [],1)
	users["460002"] = UE("460002", "IMSI", "iPhone 5S", "IMEISV", [],1 )
	users["460003"] = UE("460003", "IMSI", "LG G3", "IMEISV", [],1)
	users["460004"] = UE("460004", "IMSI", "Nokia Lumia 900", "IMEISV", [],1)
	pcef_users[1]=users
	all_users.update(users)
	users = {}
	users["462005"] = UE("462005", "IMSI", "Nokia Lumia 900", "IMEISV", [],2)
	pcef_users[2]=users
	all_users.update(users)
	for sessions in pcef_sessions.values():
		sessions.clear()
	rules.clear()
	rules["Data"] = Rule("Data", 6, 1000, 10000, 10000, 50000)
	rules["Throttle"] = Rule("Throttle", 6, 1000, 1000, 2000, 2000)
	rules["Data_Group"] = Rule("Data_Group", 6, 1000, 10000, 10000, 50000)
	rules["Throttle_Group"] = Rule("Throttle_Group", 6, 1000, 1000, 2000, 2000)
	rules["Youtube"] = Rule("Youtube", 6, 1000, 1000, 2000, 2000)

def loadDiameterErrors():	
	diameterErrors[1001] = DiameterError(1001, "DIAMETER_MULTI_ROUND_AUTH", "Subsequent messages triggered by client shall also used in Authentication and to get access of required resources. Generally used in Diameter NASSuccess")

	diameterErrors[2001] = DiameterError(2001, "DIAMETER_SUCCESS", "Request processed   Successfully ")
	diameterErrors[2002] = DiameterError(2002, "DIAMETER_LIMITED_SUCCESS", "Request is processed but some more processing is required by Server to provide access to userProtocol Errors")


	diameterErrors[3001] = DiameterError(3001, "DIAMETER_COMMAND_UNSUPPORTED", "Server returns it if Diameter Command-Code is un-recognized by server ")
	diameterErrors[3002] = DiameterError(3002, "DIAMETER_UNABLE_TO_DELIVER", "Message can't be delivered because there is no Host with Diameter URI present in Destination-Host AVP in associated Realm. ")
	diameterErrors[3003] = DiameterError(3003, "DIAMETER_REALM_NOT_SERVED", "Intended Realm is not recognized. ")
	diameterErrors[3004] = DiameterError(3004, "DIAMETER_TOO_BUSY", "Shall return by server only when server unable to provide requested service, where all the pre-requisites are also met. Client should also send the request to alternate peer. ")
	diameterErrors[3005] = DiameterError(3005, "DIAMETER_LOOP_DETECTED", "DIAMETER_REDIRECT_INDICATION3006")


	diameterErrors[3007] = DiameterError(3007, "DIAMETER_APPLICATION_UNSUPPORTED", " ")
	diameterErrors[3008] = DiameterError(3008, "DIAMETER_INVALID_HDR_BITS", "It is sent when a request is received with invalid bits combination for considered command-code in DIAMETER Header structure. E.g. Marking Proxy-Bit in CER message. ")
	diameterErrors[3009] = DiameterError(3009, "DIAMETER_INVALID_AVP_BITS", "It is sent when a request is received with invalid flag bits in an AVP. ")
	diameterErrors[3010] = DiameterError(3010, "DIAMETER_UNKNOWN_PEER", "A DIAMETER server can be configured whether it shall accept DIAMETER connection from all nodes or only   from specific nodes. If it is configured to accept connection from specific nodes and receives CER from message from any node other than specified.Here Server shall send considered erro")



	diameterErrors[4001] = DiameterError(4001, "DIAMETER_AUTHENTICATION_REJECTED", "Returned by Server, most likely because of invalid password. ")
	diameterErrors[4002] = DiameterError(4002, "DIAMETER_OUT_OF_SPACE", "Returned by node, when it receives accounting information but unable to store it because of lack of memory ")
	diameterErrors[4003] = DiameterError(4003, "ELECTION_LOST", "Peer determines that it has lost election by comparing Origin-Host value received in CER with its own DIAMETER IDENTITY and found that received DIAMETER IDENTITY is higher.Permanent Failures")

	diameterErrors[4998] = DiameterError(4998, "MZ_NO_CONNECTION_TO_PEER", "")
	diameterErrors[4998] = DiameterError(4999, "MZ_REQUEST_TIMED_OUT", "")
	diameterErrors[5001] = DiameterError(5001, "DIAMETER_AVP_UNSUPPORTED", "AVP marked with Mandatory Bit, but peer does not support it. ")
	diameterErrors[5002] = DiameterError(5002, "DIAMETER_UNKNOWN_SESSION_ID", "DIAMETER_AUTHORIZATION_REJECTED5003")


	diameterErrors[5004] = DiameterError(5004, "DIAMETER_INVALID_AVP_VALUE", "DIAMETER_MISSING_AVP5005")


	diameterErrors[5006] = DiameterError(5006, "DIAMETER_RESOURCES_EXCEEDED", "A request was received that cannot be authorized because the user      has already expended allowed resources.  An example of this error condition is a user that is restricted to one dial-up PPP port,      attempts to establish a second PPP connection. ")
	diameterErrors[5007] = DiameterError(5007, "DIAMETER_CONTRADICTING_AVPS", "Server has identified that AVPs are present that are contradictory to each other. ")
	diameterErrors[5008] = DiameterError(5008, "DIAMETER_AVP_NOT_ALLOWED", "Message is received by node (Server) that contain AVP must not be present. ")
	diameterErrors[5009] = DiameterError(5009, "DIAMETER_AVP_OCCURS_TOO_MANY_TIMES", "If message contains the a AVP number of times that exceeds permitted occurrence of AVP in message definition ")
	diameterErrors[5010] = DiameterError(5010, "DIAMETER_NO_COMMON_APPLICATION", "In response of CER if no common application supported between the peers. ")
	diameterErrors[5011] = DiameterError(5011, "DIAMETER_UNSUPPORTED_VERSION", "Self explanatory. ")
	diameterErrors[5012] = DiameterError(5012, "DIAMETER_UNABLE_TO_COMPLY", "Message rejected because of unspecified reasons. ")
	diameterErrors[5013] = DiameterError(5013, "DIAMETER_INVALID_BIT_IN_HEADER", "When an unrecognized bit in the Diameter header is set to one. ")
	diameterErrors[5014] = DiameterError(5014, "DIAMETER_INVALID_AVP_LENGTH", "Self explanatory.  ")
	diameterErrors[5015] = DiameterError(5015, "DIAMETER_INVALID_MESSAGE_LENGTH", "Self explanatory. ")
	diameterErrors[5016] = DiameterError(5016, "DIAMETER_INVALID_AVP_BIT_COMBO", "E.g. Marking AVP to Mandatory while message definition doesn't say so. ")
	diameterErrors[5017] = DiameterError(5017, "DIAMETER_NO_COMMON_SECURITY", "In response of CER if no common security mechanism supported between the peers.")
	diameterErrors[5030] = DiameterError(5030, "SUBSCRIBER_DOES_NOT_EXISTS", "Subscriber does not exists in the repository")

@app.route('/assets/<path:path>')
def send_js(path):
	print path
	return flask.send_from_directory('assets', path)

#Use cases

@app.route("/usecases", methods=["GET"])
def list_usecases():
	return render_template("usecases.html")

@app.route("/usecase/<int:id>", methods=["POST"])
def usecase_provisioning(id = None):
	func = [provisionCase1, provisionCase2, provisionCase3, provisionCase4, provisionCase5, provisionCase6]
	#print id, func[id-1]
	if func[id-1](request.form) == 0:
		flask.flash("Subscription successfully created")
		return flask.redirect("/usecases")
	else:
		abort(404)

def provisionCase5(form):
	imsi = 460001
	if len(form["IMSI"]) > 0:
		imsi = request.form["IMSI"]
	client = SoapClient(wsdl=MZ_ROOT+":12005/pcrfWSHandler?WSDL",action="",trace=False)
	response = client.addBucket(IMSI=imsi,Billcycle=2,ProductID=5)
	return response['ErrorCode']

def provisionCase4(form):
	imsi = 460004
	if len(form["IMSI"]) > 0:
		imsi = request.form["IMSI"]
	client = SoapClient(wsdl=MZ_ROOT+":12005/pcrfWSHandler?WSDL",action="",trace=False)
	response = client.addBucket(IMSI=imsi,Billcycle=2,ProductID=1)
	if response['ErrorCode'] != 0:
		return response['ErrorCode']
	response = client.addBucket(IMSI=imsi,Billcycle=2,ProductID=4)
	return response['ErrorCode']

def provisionCase3(form):
	child1 = 460002
	child2 = 460003
	if len(request.form["child1"]) > 0:
		child1 = request.form["child1"]
	if len(request.form["child2"]) > 0:
		child1 = request.form["child2"]
	client = SoapClient(wsdl=MZ_ROOT+":12005/pcrfWSHandler?WSDL",action="",trace=False)

	response = client.addBucket(IMSI="grp1",Billcycle=3,ProductID=3,Recipient="DigitalRoute")
	if response['ErrorCode'] != 0:
		return response['ErrorCode']
	response = client.addBucket(IMSI=child1,Billcycle=2,ProductID=1)
	if response['ErrorCode'] != 0:
		return response['ErrorCode']
	response = client.addBucket(IMSI=child2,Billcycle=2,ProductID=1)
	if response['ErrorCode'] != 0:
		return response['ErrorCode']
	response = client.addGroup(IMSI=child1,GroupID="grp1")
	if response['ErrorCode'] != 0:
		return response['ErrorCode']
	response = client.addGroup(IMSI=child2,GroupID="grp1")

	return response['ErrorCode']

def provisionCase2(form):
	imsi = 460001
	if len(form["IMSI"]) > 0:
		imsi = form["IMSI"]
	client = SoapClient(wsdl=MZ_ROOT+":12005/pcrfWSHandler?WSDL",action="",trace=False)
	response = client.addBucket(IMSI=imsi,Billcycle=2,ProductID=2)

	return response['ErrorCode']

def provisionCase1(form):
	imsi = 460001
	if len(form["IMSI"]) > 0:
		imsi = form["IMSI"]
	client = SoapClient(wsdl=MZ_ROOT+":12005/pcrfWSHandler?WSDL",action="",trace=False)
	response = client.addBucket(IMSI=imsi,Billcycle=2,ProductID=1)

	return response['ErrorCode']

def provisionCase6(form):
	imsi = 462005
	if len(form["IMSI"]) > 0:
		imsi = form["IMSI"]
	
	client = SoapClient(wsdl=MZ_ROOT+":12005/pcrfWSHandler?WSDL",action="",trace=False)
	response = client.addBucket(IMSI=imsi,Billcycle=2,ProductID=1)

	return response['ErrorCode']

def provisionGenericCase(imsi, productId):
	client = SoapClient(wsdl=MZ_ROOT+":12005/pcrfWSHandler?WSDL",action="",trace=False)
	response = client.addBucket(IMSI=imsi,Billcycle=2,ProductID=productId)

@app.route("/usecase/<int:id>", methods=["GET"])
def usecase_listing(id=None):
	if id<1 or id>6:
		abort(404)
	return render_template("usecase"+str(id)+".html")


# UE

@app.route("/ue/", methods=['GET'])
def list_ue():
	return render_template('list_ue.html', ues=all_users)


@app.route("/ue/<identity>", methods=['GET'])
def list_ue_sessions(identity = None):
	if not identity in all_users:
		abort(404)

	buckets = getBuckets(identity)
	return render_template('ue.html', ue = all_users[identity], buckets = buckets);

@app.route("/ue/<identity>/sessions", methods=['POST'])
def create_ue_session(identity = None):
	if not identity in all_users:
		abort(404)
	
	#Invokes the simulator on MZ
	r = forwardQuery("Start", identity)
	
	simulator_ans = r.content
	ccr_cycle = json.loads(simulator_ans)
	pcefNode = all_users[identity].pcef
	sessions = pcef_sessions[pcefNode]
	users = pcef_users[pcefNode]

	ccr_ans = ccr_cycle["Answer"]
	if ccr_ans["Result_Code"] == 2001:
		session_id = ccr_ans["Session_Id"]
		session = Session(identity, session_id, {}, [])
		sessions[session_id] = session
		users[identity].sessions.append(session)
		print "Sessions:",users[identity].sessions
		json_pretty = json.dumps(ccr_ans, sort_keys = True, indent = 4, separators = (', ', ': '))
		print "CCR Answer = ",json_pretty
		
		checkUsageMonitoringInfo(ccr_ans, session)
		checkChargingRuleName(ccr_ans, session)

		# if "Usage_Monitoring_Information"  in ccr_ans:
		# 	monitoring_info = ccr_ans["Usage_Monitoring_Information"][0]
		# 	print ("MonInfo: " + str(monitoring_info))
		# 	mkey = baToStr(monitoring_info["Monitoring_Key"])
		# 	if not mkey in session.monitoringInfo:
		# 		session.monitoringInfo[mkey] = MonitoringInfo(mkey, len(session.monitoringInfo), "", 0,0,0)

		return flask.redirect("/ue/"+identity)
	else:
		return render_template("diameter_error.html", error = diameterErrors[int(ccr_ans["Result_Code"])])

@app.route("/ue/<identity>/sessions", methods=['GET'])
def list_ue_session(identity = None):
	return flask.redirect("/ue/"+identity)

@app.route("/ue/<identity>/session/<sessionid>", methods=['GET'])
def monitor_ue_session(identity=None, sessionid = None):
	if not identity in all_users:
		abort(404)
	pcefNode = all_users[identity].pcef
	sessions = pcef_sessions[pcefNode]
	if not sessionid in sessions or sessions[sessionid].identity != identity:
		abort(404)
	buckets = getBuckets(identity)
	return render_template("session.html", session = sessions[sessionid], buckets = buckets, pcef = pcefNode)


# PCEF

@app.route("/pcef/<int:pcefid>/", methods=['GET'])
def pcef(pcefid=None):	
	buckets = {}
	users = pcef_users[pcefid]
	sessions= pcef_sessions[pcefid]
	for identity in users:
		userBuckets = getBuckets(identity)
		buckets[identity] = userBuckets
	return render_template('pcef.html', buckets=buckets,sessions=sessions.values(), users=users.values(), rules=rules.values())


@app.route("/pcef/<int:pcefid>/sessions/<sessionid>", methods=['GET'])
def monitor_pcef_session(pcefid=None,sessionid=None):
	sessions = pcef_sessions[pcefid]
	if not sessionid in sessions:
		abort(404)	
	return render_template("session.html", session = sessions[sessionid])

@app.route("/pcef/rules", methods=['GET'])
def pcef_list_rules():
	return render_template("pcef_list_rules.html", rules = rules)

@app.route("/pcef/rule/<ruleid>", methods = ['GET'])
def pcef_rule(ruleid = None):
	if not ruleid in rules:
		abort(404)
	return render_template("pcef_rule.html", rule = rules[ruleid])

@app.route("/pcef/<int:pcefid>/sessions", methods = ["GET"])
def pcef_list_sessions(pcefid=None):
	sessions = pcef_sessions[pcefid]
	return render_template("pcef_sessions.html", sessions = sessions)

@app.route("/pcef/<int:pcefid>/sessions/<sessionid>", methods = ["DELETE"])
def pcef_delete_session(pcefid=None,sessionid = None):
	print "Delete request for ", sessionid
	sessions = pcef_sessions[pcefid]
	if not sessionid in sessions:
		abort(404)
	sessions = pcef_sessions[pcefid]
	session = sessions[sessionid]
	identity = session.identity
	#return "Deleted"
	#Update the usage for each key
	simQuery={"action":"Stop"}
	simQuery["sessionid"] = session.sessionId;
	
	print simQuery
	
	ue = users[identity]._asdict()
	ue.pop("sessions", None)
	print ue
	simQuery.update(ue)
	#TODO: These parameters should be stored in the sessions object
	simQuery["rat"] = 1000 #request.args["rat"]
	simQuery["calledStationId"] = "mc@mo.com" #request.args["calledStationId"]
	
	print simQuery
	r = requests.get(MZ_ROOT+':12008/',params=simQuery)
 	simulator_ans = r.content
	ccr_cycle = json.loads(simulator_ans)
	

	ccr_ans = ccr_cycle["Answer"]
	if ccr_ans["Result_Code"] == 2001:
		session_id = ccr_ans["Session_Id"]
		
		users[identity].sessions.pop(users[identity].sessions.index(session))
		sessions.pop(sessionid)

		json_pretty = json.dumps(ccr_ans, sort_keys = True, indent = 4, separators = (', ', ': '))
		print "CCR_Answer=", json_pretty

		checkUsageMonitoringInfo(ccr_ans, session)
		checkChargingRuleName(ccr_ans, session)

		# Code 303 forces the browser to change the method to GET
		return flask.redirect("/ue/"+identity, code=303)
	else:
		return render_template("diameter_error.html", error = diameterErrors[int(ccr_ans["Result_Code"])])


@app.route("/pcef/<int:pcefid>/sessions/<sessionid>", methods = ["POST"])
def pcef_report_session_usage(sessionid = None, pcefid=None):
	if not sessionid in pcef_sessions[pcefid]:
		abort(404)
	sessions = pcef_sessions[pcefid]
	users = pcef_users[pcefid]
	session = sessions[sessionid]
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
	
	ue = users[identity]._asdict()
	ue.pop("sessions", None)
	print ue
	simQuery.update(ue)
	#TODO: These parameters should be stored in the sessions object
	simQuery["rat"] = 1000 #request.args["rat"]
	simQuery["calledStationId"] = "mc@mo.com" #request.args["calledStationId"]
	
	print simQuery
	r = requests.get(MZ_ROOT+':12008/',params=simQuery)
 	simulator_ans = r.content
	ccr_cycle = json.loads(simulator_ans)
	

	ccr_ans = ccr_cycle["Answer"]
	session_id = ccr_ans["Session_Id"]
	
	json_pretty = json.dumps(ccr_ans, sort_keys = True, indent = 4, separators = (', ', ': '))
	print "CCR_Answer=", json_pretty

	if ccr_ans["Result_Code"] != 2001:
		code = ccr_ans["Result_Code"]
		flask.flash("Diameter Error: "+ str(diameterErrors[code].id) + " " + diameterErrors[code].code + " " + diameterErrors[code].description)
	checkUsageMonitoringInfo(ccr_ans, session)
	checkChargingRuleName(ccr_ans, session)
	
	buckets = getBuckets(identity)
	

	return render_template("session.html", session = session, buckets = buckets)

def getBuckets(identity):
	simQuery={"action":"Refresh", "identity":identity}
	# ue = users[identityid]._asdict()
	# ue.pop("sessions", None)
	# print ue
	# simQuery.update(ue)
	r = requests.get(MZ_ROOT+':12008/',params=simQuery)
	simulator_ans = r.content
	buckets = json.loads(simulator_ans)
	json_pretty = json.dumps(buckets, sort_keys = True, indent = 4, separators = (', ', ': '))
	print "Buckets=", json_pretty
	return buckets

@app.route("/bdh", methods=["GET"])
def show_bucket_data_holder():
	buckets = {}
	for identityid in all_users:
		userBuckets = getBuckets(identityid)		
		buckets[identityid] = userBuckets;
	userBuckets = getBuckets("grp1")
	buckets["grp1"] = userBuckets;
	return render_template("bdh.html", buckets = buckets)


# @app.route("/bdh", methods=["POST"])
# def manage_bdh():
# 	if "action" in request.form:
# 		simQuery={"action":request.form["action"]}

# 		r = requests.get(MZ_ROOT+':12008/',params=simQuery)
#  		simulator_ans = r.content
 	

@app.route("/bdh/<identityid>", methods=["GET"])
def view_bdh(identityid=None):
	if not identityid in all_users and identityid != "grp1":
		abort(404)

	buckets = getBuckets(identityid);
	
	return render_template("ue_bdh.html", identityid = identityid, buckets = buckets)

@app.route("/bdh/<identity>", methods=["POST"])
def reset_bdh(identity=None):
	if not identity in all_users and identity!="grp1":
		abort(404)

	if "action" in request.form and request.form["action"] == "Reset BDH":
		initialize()
		simQuery={"action":"Reset BDH", "identity":identity}
		# ue = users[identityid]._asdict()
		# ue.pop("sessions", None)
		# print ue
		# simQuery.update(ue)
		r = requests.get(MZ_ROOT+':12008/',params=simQuery)
		simulator_ans = r.content
		buckets = json.loads(simulator_ans)
		json_pretty = json.dumps(buckets, sort_keys = True, indent = 4, separators = (', ', ': '))
		print "Buckets=", json_pretty
		return flask.redirect("/bdh")
			#ue_bdh.html", identityid = identityid, buckets = buckets)
	abort(404)

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
	if "Charging_Rule_Install" in ccr_ans:
		for chargingRule in ccr_ans["Charging_Rule_Install"]:
			for chargingRuleName in chargingRule["Charging_Rule_Name"]:
				session.installedRules.append(baToStr(chargingRuleName))
				flask.flash("Rule to install "+baToStr(chargingRuleName))
	if "Charging_Rule_Remove" in ccr_ans:
		for chargingRule in ccr_ans["Charging_Rule_Remove"]:
			for chargingRuleName in chargingRule["Charging_Rule_Name"]:
				if baToStr(chargingRuleName) in session.installedRules:
					index = session.installedRules.index(baToStr(chargingRuleName))
					flask.flash("Rule to remove "+baToStr(chargingRuleName))
					session.installedRules.pop(index)


def baToStr(byteArray):
	return "".join([chr(c) for c in byteArray])

def printSessions(sessions):
	print "Sessions"
	for sessions in pcef_sessions.values():
		for s in sessions:
			print s.identity, s.monitoringInfo
			for minfo  in s.monitoringInfo.values():
				print minfo.key, minfo.gsu, minfo.usage

def forwardQuery(type, identity):
	simQuery = {}
	simQuery = {"action":type}
	ue = all_users[identity]._asdict()
	ue.pop("sessions", None)
	simQuery.update(ue)
	simQuery["rat"] = 1000 #request.args["rat"]
	simQuery["calledStationId"] = "mc@mo.com" #request.args["calledStationId"]
	pcefNode = all_users[identity].pcef
	return requests.get(MZ_ROOT+':'+PCEF_PORT[pcefNode]+'/',params=simQuery)

def datetimeformat(value, format="%Y-%m-%d %H-%M-%S"):
	return value.strftime(format)


environment = jinja2.Environment()
environment.filters['datetimeformat'] = datetimeformat
initialize()
loadDiameterErrors()
if __name__ == "__main__":
	app.secret_key = 'AhHKJyig781641hshkjh-=HA'
	app.debug = True
	app.run()
