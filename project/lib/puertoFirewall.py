class PuertoFirewall(object):
	carga_ovs_intranet = 0
	carga_ovs_extranet = 0
	def __init__(self, interfaz_puerto_ovs_intranet, interfaz_puerto_ovs_extranet, puertoFirewallNombre ):
		self.interfaz_puerto_ovs_intranet = interfaz_puerto_ovs_intranet
		self.interfaz_puerto_ovs_extranet = interfaz_puerto_ovs_extranet
		self.puertoFirewallNombre = puertoFirewallNombre
	def carga_representativa(self):
		return max([self.carga_ovs_intranet,self.carga_ovs_extranet])
	