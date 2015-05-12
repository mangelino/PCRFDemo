class UE:
	def __init__(self, identity, identityType, userEquipment, userEquipmentType):
		self.identity = identity
		self.identityType = identityType
		self.userEquipment = userEquipment
		self.userEquipmentType = userEquipmentType
		self.sessions = []
		self.pcef = None

	def assignPCEF(self, pcef):
		self.pcef = pcef

	def _asdict(self):
		res = {}
		res["identity"] = self.identity
		res["identityType"] = self.identityType
		res["userEquipment"] = self.userEquipment
		res["userEquipmentType"] = self.userEquipmentType
		return res