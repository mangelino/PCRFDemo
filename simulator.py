from flask import Flask
from flask import render_template
import flask
from flask import abort
from flask import request
import requests
import json
import jinja2
import datetime
from dateutil import parser

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
	

@app.route('/')
def root():
	return render_template("landing.html", mzIP=MZ_ROOT)


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
	func = [provisionCase1, provisionCase2, provisionCase3, provisionCase4, provisionCase5, provisionCase6, provisionCase7]
	#print id, func[id-1]
	res = func[id-1](request.form)
	if res == 0:
		flask.flash("Subscription successfully created")
		
	else:
		flask.flash("Error"+str(res))

	return flask.redirect("/usecases")

def provisionCase5(form):
	imsi = 460001
	prodId=0
	if len(form["IMSI"]) > 0:
		imsi = request.form["IMSI"]
	if len(form["ProductID"]) > 0:
		prodId = int(request.form["ProductID"])
	else:
		return "Missing Product ID to provision. Enter the Product ID shown in the Service Control screen from MZ"
	client = SoapClient(wsdl=MZ_ROOT+":12005/pcrfWSHandler?WSDL",action="",trace=False)
	response = client.addBucket(IMSI=imsi,Billcycle=2,ProductID=prodId)
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

def provisionCase7(form):
	imsi = 462005
	if len(form["IMSI"]) > 0:
		imsi = form["IMSI"]
	
	client = SoapClient(wsdl=MZ_ROOT+":12005/pcrfWSHandler?WSDL",action="",trace=False)
	response = client.addBucket(IMSI=imsi,Billcycle=2,ProductID=6)

	return response['ErrorCode']

def provisionGenericCase(imsi, productId):
	client = SoapClient(wsdl=MZ_ROOT+":12005/pcrfWSHandler?WSDL",action="",trace=False)
	response = client.addBucket(IMSI=imsi,Billcycle=2,ProductID=productId)

@app.route("/usecase/<int:id>", methods=["GET"])
def usecase_listing(id=None):
	if id<1 or id>7:
		abort(404)
	return render_template("usecase"+str(id)+".html")


# UE

@app.route("/ue/", methods=['GET'])
def list_ue():
	print all_users.keys()
	return render_template('list_ue.html', ues=sorted(all_users.values(), key=lambda k: k.identity))


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
		notifyRules(res[2])
		return flask.redirect("/ue/"+identity+"/session/"+res[1].sessionId)
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

@app.route("/ue/<identity>/session/json/<sessionid>", methods=['GET'])
def monitor_ue_session_json(identity=None, sessionid = None):
	if not identity in all_users:
		abort(404)
	pcef = all_users[identity].pcef
	sessions = pcef.sessions
	if not sessionid in sessions or sessions[sessionid].identity != identity:
		abort(404)
	buckets = getBuckets(identity)
	session = sessions[sessionid]
	return json.dumps(dict(session = dict(sessionid=session.sessionId,  monitoringInfo=session.monitoringInfo,rules=list(session.installedRules)), buckets = buckets, pcef = dict(id = pcef.id, rules = pcef.rules)))


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
	return render_template('pcef.html', buckets=buckets,sessions=sessions.values(), users=users.values(), rules=pcefs[pcefid].rules.values(), pcef=pcefid)


@app.route("/pcef/<int:pcefid>/sessions/<sessionid>", methods=['GET'])
def monitor_pcef_session(pcefid=None,sessionid=None):
	sessions = pcefs[pcefid].sessions
	if not sessionid in sessions:
		abort(404)	
	return render_template("session.html", pcefid = pcefid, session = sessions[sessionid])

@app.route("/pcef/<int:pcefid>/rules", methods=['GET'])
def pcef_list_rules(pcefid=None):
	return render_template("pcef_list_rules.html", rules = pcefs[pcefid].rules)

@app.route("/pcef/<int:pcefid>/rule/<ruleid>", methods = ['GET'])
def pcef_rule(ruleid = None, pcefid=None):
	if not ruleid in pcefs[pcefid].rules:
		abort(404)
	return render_template("pcef_rule.html", rule = pcefs[pcefid].rules[ruleid])

@app.route("/pcef/<int:pcefid>/sessions", methods = ["GET"])
def pcef_list_sessions(pcefid=None):
	sessions = pcefs[pcefid].sessions
	return render_template("pcef_sessions.html", sessions = sessions)

@app.route("/pcef/<int:pcefid>/sessions/delete/<sessionid>", methods = ["POST"])
def pcef_delete_session(pcefid=None,sessionid = None):
	print "Delete request for ", sessionid
	if not sessionid in pcefs[pcefid].sessions:
		abort(404)
	session = pcefs[pcefid].sessions[sessionid]
	identity = session.identity

	result_code = pcefs[pcefid].terminateUESession(sessionid)
	if result_code == PCC.DIAMETER_SUCCESS:
		return flask.redirect("/ue/"+identity, code=303)
	else:
		return render_template("diameter_error.html", error = PCC.diameterErrors[result_code])


@app.route("/pcef/<int:pcefid>/sessions/<sessionid>", methods = ["POST"])
def pcef_report_session_usage(sessionid = None, pcefid=None):
	if not sessionid in pcefs[pcefid].sessions:
		abort(404)

	res = pcefs[pcefid].reportSessionUsage(sessionid, request)
	if (res[0] != PCC.DIAMETER_SUCCESS):
		code = res[0]
		flask.flash("Diameter Error: "+ str(diameterErrors[code].id) + " " + diameterErrors[code].code + " " + diameterErrors[code].description)
	else:
		notifyRules(res[1])
		#return flask.redirect("/pcef/"+str(pcefid)+"/sessions/"+sessionid)
	session = pcefs[pcefid].sessions[sessionid]
	buckets = getBuckets(session.identity)
	
	return render_template("session.html", session = session, buckets = buckets, pcef = pcefs[pcefid])

@app.route("/pcef/<int:pcefid>/sessions/json/<sessionid>", methods = ["POST"])
def pcef_report_session_usage_json(sessionid = None, pcefid=None):
	if not sessionid in pcefs[pcefid].sessions:
		abort(404)

	res = pcefs[pcefid].reportSessionUsage(sessionid, request)
	if (res[0] != PCC.DIAMETER_SUCCESS):
		code = res[0]
		flask.flash("Diameter Error: "+ str(diameterErrors[code].id) + " " + diameterErrors[code].code + " " + diameterErrors[code].description)
	else:
		notifyRules(res[1])
		#return flask.redirect("/pcef/"+str(pcefid)+"/sessions/"+sessionid)
	session = pcefs[pcefid].sessions[sessionid]
	buckets = getBuckets(session.identity)
	pcef = pcefs[pcefid]
	return json.dumps(dict(session = dict(sessionid=session.sessionId, monitoringInfo=session.monitoringInfo, rules=list(session.installedRules)), buckets = buckets, pcef = dict(id = pcef.id, rules = pcef.rules)))

@app.route("/pcef/<int:pcefid>/messages", methods=["GET"])
def pcef_messages(pcefid = None):
	if not pcefid in pcefs:
		abort(404)
	pcef = pcefs[pcefid]
	jumly = getJumlyScript(pcef.messages)
	return render_template("messages.html", jumly = jumly)

def getJumlyScript(messages):
	script = ""

	for m in messages:
		if m.type == "A":
			script += ', -> @reply "{0}{1}({2})"'.format(m.name, m.type, m.subtype)
			current_from = None
			current_to = None
		else:
			script += '\n@found "{0}", -> @message "{1}{2}({3})", "{4}"'.format(m.fr, m.name, m.type, m.subtype, m.to)
	return script


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
 	

@app.route("/bdh/<identity>", methods=["POST"])
def reset_bdh(identity=None):
	if not identity in all_users and identity!="grp1":
		abort(404)

	if "action" in request.form and request.form["action"].startswith("Remove"):
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
		return flask.redirect(request.referrer)
			#ue_bdh.html", identityid = identityid, buckets = buckets)
	abort(404)


@app.context_processor
def my_utilities():

	def date_now():
		return datetime.datetime.now()

	def unicodeToDatetime(unicodeDate):
		return parser.parse(unicodeDate).replace(tzinfo=None)

	return dict(date_now=date_now, unicodeToDatetime=unicodeToDatetime)


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
	users["460004"] = UE("460004", "IMSI", "Sony Xperia", "IMEISV")
	for ue in users.values():
		pcefs[1].registerUE(ue)

	all_users.update(users)
	users = {}
	users["462005"] = UE("462005", "IMSI", "Sony Xperia", "IMEISV", 1)
	
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
	app.run(host="0.0.0.0")
