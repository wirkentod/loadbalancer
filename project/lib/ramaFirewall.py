class RamaFirewall(object):
	carga_ovs_intranet = 0
	carga_ovs_extranet = 0
	def __init__(self, interfaz_puerto_ovs_intranet, interfaz_puerto_ovs_extranet, groupID_ovs_intranet, ramaFirewallNombre, estado, flagtmp, SubRedes):
		self.interfaz_puerto_ovs_intranet = interfaz_puerto_ovs_intranet
		self.interfaz_puerto_ovs_extranet = interfaz_puerto_ovs_extranet
		self.groupID_ovs_intranet = groupID_ovs_intranet
		self.ramaFirewallNombre = ramaFirewallNombre
		self.estado = estado
		self.flagtmp = flagtmp
		self.SubRedes = SubRedes
		#Se agrega nuevos atributos
		self.flagtmp_old = ""
		self.temp_bloqueado = ""
		self.timeHOsessions = ""
	def carga_representativa(self):
		return max([self.carga_ovs_intranet,self.carga_ovs_extranet])
	
