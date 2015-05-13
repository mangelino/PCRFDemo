from collections import namedtuple

DIAMETER_SUCCESS = 2001

Rule = namedtuple("Rule", "name qos uploadMin_kbs downloadMin_kbs uploadMax_kbs downloadMax_kbs")
MonitoringInfo = namedtuple("MonitoringInfo", "key intKey productName gsu usu usage")
Session = namedtuple("UserPolicy", "identity sessionId monitoringInfo installedRules atHomeLocation")

DiameterError = namedtuple("DiamaterError", "id code description")
diameterErrors = {}

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

class RulesActions:
	def __init__(self):
		self.install = set()
		self.remove = set()

	def merge(self, rules):
		self.install = self.install.union(rules.install).difference(rules.remove)
		self.remove = self.remove.union(rules.remove).difference(rules.install)

	def installRule(self, rule):
		if rule in self.remove:
			self.remove.remove(rule)
		else:
			self.install.add(rule)

	def removeRule(self, rule):
		if rule in self.install:
			self.install.remove(rule)
		else:
			self.remove.add(rule)

	def asDict(self):
		return {"install":list(self.install), "remove":list(self.remove)}