class RamaFirewall(object):
	carga_ovs_intranet = 0
	carga_ovs_extranet = 0
	def __init__(self, interfaz_puerto_ovs_intranet, interfaz_puerto_ovs_extranet, ramaFirewallNombre, estado, flagtmp):
		self.interfaz_puerto_ovs_intranet = interfaz_puerto_ovs_intranet
		self.interfaz_puerto_ovs_extranet = interfaz_puerto_ovs_extranet
		self.ramaFirewallNombre = ramaFirewallNombre
		self.estado = estado
		self.flagtmp = flagtmp
	def carga_representativa(self):
		return max([self.carga_ovs_intranet,self.carga_ovs_extranet])
	