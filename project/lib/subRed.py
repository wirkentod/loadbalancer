class SubRed(object):
	def __init__(self, nombre, ip_mask, packetCount_old, bytesConsumidos_old, duration_old, pps, bps):
		self.nombre = nombre
		self.ip_mask = ip_mask
		self.packetCount_old = packetCount_old
		self.bytesConsumidos_old = bytesConsumidos_old
		self.duration_old = duration_old
		self.pps = pps
		self.bps = bps
	def get_packetCount_old(self):
		return self.packetCount_old
	def set_packetCount_old(self, packetCount_old):
		self.packetCount_old = packetCount_old