from flask import Flask
from flask import render_template
import flask
from flask import abort
from flask import request
import requests
import json
import jinja2

from pysimplesoap.client import SoapClient
from UE import UE
from PCEF import PCEF
from PCC import Rule, MonitoringInfo, Session, diameterErrors
import PCC

app = Flask(__name__)

MZ_ROOT = "http://192.168.56.101"
PCEF_PORT = {1:"12008", 2:"12009"}

all_users = {}

pcefs = {}
rules = {}
allowed_actions = ["Start", "Stop", "Update", "Refresh", "Reset"]

def initialize():
	pcefs.clear()
	pcefs[1]= PCEF(1, "PCEF v1", MZ_ROOT, PCEF_PORT[1])
	pcefs[2]= PCEF(2, "PCEF v2", MZ_ROOT, PCEF_PORT[2])

	createDefaultUsersAndRegister()
	print "Init users: ", all_users
	

# def loadDiameterErrors():	
# 	diameterErrors[1001] = DiameterError(1001, "DIAMETER_MULTI_ROUND_AUTH", "Subsequent messages triggered by client shall also used in Authentication and to get access of required resources. Generally used in Diameter NASSuccess")

# 	diameterErrors[2001] = DiameterError(2001, "DIAMETER_SUCCESS", "Request processed   Successfully ")
# 	diameterErrors[2002] = DiameterError(2002, "DIAMETER_LIMITED_SUCCESS", "Request is processed but some more processing is required by Server to provide access to userProtocol Errors")


# 	diameterErrors[3001] = DiameterError(3001, "DIAMETER_COMMAND_UNSUPPORTED", "Server returns it if Diameter Command-Code is un-recognized by server ")
# 	diameterErrors[3002] = DiameterError(3002, "DIAMETER_UNABLE_TO_DELIVER", "Message can't be delivered because there is no Host with Diameter URI present in Destination-Host AVP in associated Realm. ")
# 	diameterErrors[3003] = DiameterError(3003, "DIAMETER_REALM_NOT_SERVED", "Intended Realm is not recognized. ")
# 	diameterErrors[3004] = DiameterError(3004, "DIAMETER_TOO_BUSY", "Shall return by server only when server unable to provide requested service, where all the pre-requisites are also met. Client should also send the request to alternate peer. ")
# 	diameterErrors[3005] = DiameterError(3005, "DIAMETER_LOOP_DETECTED", "DIAMETER_REDIRECT_INDICATION3006")


# 	diameterErrors[3007] = DiameterError(3007, "DIAMETER_APPLICATION_UNSUPPORTED", " ")
# 	diameterErrors[3008] = DiameterError(3008, "DIAMETER_INVALID_HDR_BITS", "It is sent when a request is received with invalid bits combination for considered command-code in DIAMETER Header structure. E.g. Marking Proxy-Bit in CER message. ")
# 	diameterErrors[3009] = DiameterError(3009, "DIAMETER_INVALID_AVP_BITS", "It is sent when a request is received with invalid flag bits in an AVP. ")
# 	diameterErrors[3010] = DiameterError(3010, "DIAMETER_UNKNOWN_PEER", "A DIAMETER server can be configured whether it shall accept DIAMETER connection from all nodes or only   from specific nodes. If it is configured to accept connection from specific nodes and receives CER from message from any node other than specified.Here Server shall send considered erro")



# 	diameterErrors[4001] = DiameterError(4001, "DIAMETER_AUTHENTICATION_REJECTED", "Returned by Server, most likely because of invalid password. ")
# 	diameterErrors[4002] = DiameterError(4002, "DIAMETER_OUT_OF_SPACE", "Returned by node, when it receives accounting information but unable to store it because of lack of memory ")
# 	diameterErrors[4003] = DiameterError(4003, "ELECTION_LOST", "Peer determines that it has lost election by comparing Origin-Host value received in CER with its own DIAMETER IDENTITY and found that received DIAMETER IDENTITY is higher.Permanent Failures")

# 	diameterErrors[4998] = DiameterError(4998, "MZ_NO_CONNECTION_TO_PEER", "")
# 	diameterErrors[4998] = DiameterError(4999, "MZ_REQUEST_TIMED_OUT", "")
# 	diameterErrors[5001] = DiameterError(5001, "DIAMETER_AVP_UNSUPPORTED", "AVP marked with Mandatory Bit, but peer does not support it. ")
# 	diameterErrors[5002] = DiameterError(5002, "DIAMETER_UNKNOWN_SESSION_ID", "DIAMETER_AUTHORIZATION_REJECTED5003")


# 	diameterErrors[5004] = DiameterError(5004, "DIAMETER_INVALID_AVP_VALUE", "DIAMETER_MISSING_AVP5005")


# 	diameterErrors[5006] = DiameterError(5006, "DIAMETER_RESOURCES_EXCEEDED", "A request was received that cannot be authorized because the user      has already expended allowed resources.  An example of this error condition is a user that is restricted to one dial-up PPP port,      attempts to establish a second PPP connection. ")
# 	diameterErrors[5007] = DiameterError(5007, "DIAMETER_CONTRADICTING_AVPS", "Server has identified that AVPs are present that are contradictory to each other. ")
# 	diameterErrors[5008] = DiameterError(5008, "DIAMETER_AVP_NOT_ALLOWED", "Message is received by node (Server) that contain AVP must not be present. ")
# 	diameterErrors[5009] = DiameterError(5009, "DIAMETER_AVP_OCCURS_TOO_MANY_TIMES", "If message contains the a AVP number of times that exceeds permitted occurrence of AVP in message definition ")
# 	diameterErrors[5010] = DiameterError(5010, "DIAMETER_NO_COMMON_APPLICATION", "In response of CER if no common application supported between the peers. ")
# 	diameterErrors[5011] = DiameterError(5011, "DIAMETER_UNSUPPORTED_VERSION", "Self explanatory. ")
# 	diameterErrors[5012] = DiameterError(5012, "DIAMETER_UNABLE_TO_COMPLY", "Message rejected because of unspecified reasons. ")
# 	diameterErrors[5013] = DiameterError(5013, "DIAMETER_INVALID_BIT_IN_HEADER", "When an unrecognized bit in the Diameter header is set to one. ")
# 	diameterErrors[5014] = DiameterError(5014, "DIAMETER_INVALID_AVP_LENGTH", "Self explanatory.  ")
# 	diameterErrors[5015] = DiameterError(5015, "DIAMETER_INVALID_MESSAGE_LENGTH", "Self explanatory. ")
# 	diameterErrors[5016] = DiameterError(5016, "DIAMETER_INVALID_AVP_BIT_COMBO", "E.g. Marking AVP to Mandatory while message definition doesn't say so. ")
# 	diameterErrors[5017] = DiameterError(5017, "DIAMETER_NO_COMMON_SECURITY", "In response of CER if no common security mechanism supported between the peers.")
# 	diameterErrors[5030] = DiameterError(5030, "SUBSCRIBER_DOES_NOT_EXISTS", "Subscriber does not exists in the repository")

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
	print all_users.keys()
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
	
	pcef = all_users[identity].pcef
	res = pcef.createUESession(identity)

	if res[0] == PCC.DIAMETER_SUCCESS:
		notifyRules(res[1])
		return flask.redirect("/ue/"+identity)
	else:
		return render_template("diameter_error.html", error = diameterErrors[int(res[0])])

@app.route("/ue/<identity>/sessions", methods=['GET'])
def list_ue_session(identity = None):
	return flask.redirect("/ue/"+identity)

@app.route("/ue/<identity>/session/<sessionid>", methods=['GET'])
def monitor_ue_session(identity=None, sessionid = None):
	if not identity in all_users:
		abort(404)
	pcef = all_users[identity].pcef
	sessions = pcef.sessions
	if not sessionid in sessions or sessions[sessionid].identity != identity:
		abort(404)
	buckets = getBuckets(identity)
	return render_template("session.html", session = sessions[sessionid], buckets = buckets, pcef = pcef)


# PCEF

@app.route("/pcef/", methods=['GET'])
def pcef_list():
	return render_template("pcef_list.html", pcefs=pcefs.values())

@app.route("/pcef/<int:pcefid>/", methods=['GET'])
def pcef(pcefid=None):	
	buckets = {}
	users = pcefs[pcefid].users
	sessions= pcefs[pcefid].sessions
	for identity in users:
		userBuckets = getBuckets(identity)
		buckets[identity] = userBuckets
	return render_template('pcef.html', buckets=buckets,sessions=sessions.values(), users=users.values(), rules=pcefs[pcefid].rules.values())


@app.route("/pcef/<int:pcefid>/sessions/<sessionid>", methods=['GET'])
def monitor_pcef_session(pcefid=None,sessionid=None):
	sessions = pcefs[pcefid].sessions
	if not sessionid in sessions:
		abort(404)	
	return render_template("session.html", session = sessions[sessionid])

@app.route("/pcef/<int:pcefid>/rules", methods=['GET'])
def pcef_list_rules(pcefid=None):
	return render_template("pcef_list_rules.html", rules = pcefs[pcefid].rules)

@app.route("/pcef/rule/<ruleid>", methods = ['GET'])
def pcef_rule(ruleid = None):
	if not ruleid in rules:
		abort(404)
	return render_template("pcef_rule.html", rule = rules[ruleid])

@app.route("/pcef/<int:pcefid>/sessions", methods = ["GET"])
def pcef_list_sessions(pcefid=None):
	sessions = pcefs[pcefid].sessions
	return render_template("pcef_sessions.html", sessions = sessions)

@app.route("/pcef/<int:pcefid>/sessions/<sessionid>", methods = ["DELETE"])
def pcef_delete_session(pcefid=None,sessionid = None):
	print "Delete request for ", sessionid
	if not sessionid in pcefs[pcefid].sessions:
		abort(404)

	result_code = pcefs[pcefid].terminateUESession(identity)
	if result_code == DIAMETER_SUCCESS:
		return flask.redirect("/ue/"+identity, code=303)
	else:
		return render_template("diameter_error.html", error = diameterErrors[result_code])


@app.route("/pcef/<int:pcefid>/sessions/<sessionid>", methods = ["POST"])
def pcef_report_session_usage(sessionid = None, pcefid=None):
	if not sessionid in pcefs[pcefid].sessions:
		abort(404)

	res = pcefs[pcefid].reportSessionUsage(sessionid, request)
	if (res[0] != PCC.DIAMETER_SUCCESS):
		code = res[0]
		flask.flash("Diameter Error: "+ str(diameterErrors[code].id) + " " + diameterErrors[code].code + " " + diameterErrors[code].description)
	
	notifyRules(res[1])
	buckets = getBuckets(identity)
	
	return render_template("session.html", session = session, buckets = buckets)

def notifyRules(rules):
	for k in rules.keys():
			for r in rules[k]:
				flask.flash("Rules to "+k+" "+r)

def getBuckets(identity):
	simQuery={"action":"Refresh", "identity":identity}
	
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



# def forwardQuery(type, identity):
# 	simQuery = {}
# 	simQuery = {"action":type}
# 	ue = all_users[identity]._asdict()
	
# 	simQuery.update(ue)
# 	simQuery["rat"] = 1000 #request.args["rat"]
# 	simQuery["calledStationId"] = "mc@mo.com" #request.args["calledStationId"]
# 	pcefNode = all_users[identity].pcef
# 	return requests.get(MZ_ROOT+':'+PCEF_PORT[pcefNode]+'/',params=simQuery)

def datetimeformat(value, format="%Y-%m-%d %H-%M-%S"):
	return value.strftime(format)

#
# Init
#
def createDefaultUsersAndRegister():
	print "Initializing default values..."

	users = {}
	users["460001"] = UE("460001", "IMSI", "Samsung Galaxy S4", "IMEISV")
	users["460002"] = UE("460002", "IMSI", "iPhone 5S", "IMEISV")
	users["460003"] = UE("460003", "IMSI", "LG G3", "IMEISV")
	users["460004"] = UE("460004", "IMSI", "Nokia Lumia 900", "IMEISV")
	for ue in users.values():
		pcefs[1].registerUE(ue)

	all_users.update(users)
	users = {}
	users["462005"] = UE("462005", "IMSI", "Nokia Lumia 900", "IMEISV")
	
	for ue in users.values():
		pcefs[2].registerUE(ue)

	all_users.update(users)
	print ("...done")
	print all_users	


environment = jinja2.Environment()
environment.filters['datetimeformat'] = datetimeformat
initialize()
PCC.loadDiameterErrors()
if __name__ == "__main__":
	app.secret_key = 'AhHKJyig781641hshkjh-=HA'
	app.debug = True
	app.run()
