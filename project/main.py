import sys
import json
import csv
import sched
import time

from lib import StaticEntryPusher
from lib import RestApiFloodlight
from lib import RamaFirewall
from lib import SubRed

#iniciamos las variables globales

ip_controller = '10.20.10.26'
ovs_intranet_DPID = "00:00:5a:9d:cb:0b:01:4b"
ovs_extranet_DPID = "00:00:d2:d8:cc:51:e3:4f"

#Definimos las ramas correspondientes a cada Firewall
rama1 = RamaFirewall('3','1','rama1','NORMAL','ESTABLE',[])
rama2 = RamaFirewall('2','4','rama2','NORMAL','ESTABLE',[])
rama3 = RamaFirewall('6','5','rama3','NORMAL','ESTABLE',[])
#Rama Sensor Spare
rama4 = RamaFirewall('1','6','rama4','NORMAL','ESTABLE',[])

arreglo_ramas_Firewall = [rama1,rama2,rama3]
arreglo_SubRedes = []
arreglo_rama_HandOff_src = []
arreglo_rama_HandOff_dst = []

umbral_HandOff = 1000 #bps


pusher = StaticEntryPusher(ip_controller)

def crearFlowEntriesPorSubNet(fileName):
	#Creamos los flow entries por defecto
	flow_Default_SubNet_intranet = {
			'switch':ovs_intranet_DPID,
			"name": "default_intranet",
			"cookie":"0",
			"priority":"0",
			"active":"true",
			"actions":"output=4"
			}
	flow_Default_SubNet_extranet = {
			'switch':ovs_extranet_DPID,
			"name": "default_extranet",
			"cookie":"0",
			"priority":"0",
			"active":"true",
			"actions":"output=2"
			}
	pusher.set(flow_Default_SubNet_intranet)
	pusher.set(flow_Default_SubNet_extranet)
	
	#Asignamos las SubRedes a cada rama
	i = 0
	cantidadFirewalls = len(arreglo_ramas_Firewall)
	for subRedName, prefijo in csv.reader(open('./subnets/'+str(fileName)+'.csv')):
		indice = i % cantidadFirewalls
		#Inicializamos las SubRedes a cada Rama
		sub_red = SubRed(str(subRedName),str(prefijo),0,0,0,0,0)
		arreglo_SubRedes.append(sub_red)
		arreglo_ramas_Firewall[indice].SubRedes.append(sub_red)
		#Creamos las reglas por cada SubRed
		flowSubNet_intranet = {
			'switch':ovs_intranet_DPID,
			"name":str(subRedName) + "_intranet",
			"cookie":"0",
			"priority":"10",
			"eth_type ":"0x0800",
			"ipv4_src":str(prefijo),
			"active":"true",
			"in_port":"4",
			"actions":"output=" + str(arreglo_ramas_Firewall[indice].interfaz_puerto_ovs_intranet)
			}

		flowSubNet_extranet = {
			'switch':ovs_extranet_DPID,
			"name":str(subRedName) + "_extranet",
			"cookie":"0",
			"priority":"10",
			"eth_type ":"0x0800",
			"ipv4_dst":str(prefijo),
			"active":"true",
			"in_port":"4",
			"actions":"output=" + str(arreglo_ramas_Firewall[indice].interfaz_puerto_ovs_extranet)
			}

		pusher.set(flowSubNet_intranet)
		pusher.set(flowSubNet_extranet)
		i = i + 1	

def medirBps_Ovs(puerto, direction, ovs_PID):
	rest = RestApiFloodlight(ip_controller)
	data = rest.measureLoad(ovs_PID, str(puerto))
	j = json.loads(data)
	key = 'bits-per-second-' + direction
	return j[0][str(key)]
	

def medirFlows_Ovs(ovs_PID):
	rest = RestApiFloodlight(ip_controller)
	data = rest.measureFlows(ovs_PID)
	j = json.loads(data)
	arr_flows_PID = j['flows']
	dict_Flows = {}
	#transformamos la data en el json a un diccionario
	for flow in arr_flows_PID:
		try:
			duration_sec = float(flow['duration_sec'])
			duration_nsec = float(flow['duration_nsec'])
			duration = duration_sec + (duration_nsec/1e9)
			#values = [packet_count, byte_count, duration]
			values = [int(flow['packet_count']), int(flow['byte_count']), duration]
			new_flow = {str(flow['match']['ipv4_src']): values}
			dict_Flows.update(new_flow)
		except KeyError, e:
			pass
	#print dict_Flows
	return dict_Flows

def guardarInformacionDicts_Load_Net():
	for puerto in arreglo_puertos_Firewall:
                load_inst_puerto_intranet = medirBps_Ovs(puerto.interfaz_puerto_ovs_intranet, 'tx', ovs_intranet_DPID)
                puerto.carga_ovs_intranet = load_inst_puerto_intranet
                dict_load_intranet[str(puerto.puertoFirewallNombre)].append(float(load_inst_puerto_intranet))

#scheduler		
s = sched.scheduler(time.time, time.sleep)
def accionCadaXSegundos():
	
	#Actualizamos las mediciones en cada Rama
	for rama in arreglo_ramas_Firewall:
		load_inst_puerto_intranet = medirBps_Ovs(rama.interfaz_puerto_ovs_intranet, 'tx', ovs_intranet_DPID)
		load_inst_puerto_extranet = medirBps_Ovs(rama.interfaz_puerto_ovs_extranet, 'tx', ovs_extranet_DPID)
		rama.carga_ovs_intranet = load_inst_puerto_intranet  
		rama.carga_ovs_extranet = load_inst_puerto_extranet
		carga_representativa = rama.carga_representativa()
		
		#Si pasa el umbral
		if float(carga_representativa) > float(umbral_HandOff):
			rama.flagtmp = 'INESTABLE'
			if not rama in arreglo_rama_HandOff_src :
				arreglo_rama_HandOff_src.append(rama)
		else :
			rama.flagtmp = 'ESTABLE'
			if not rama in arreglo_rama_HandOff_dst :
				arreglo_rama_HandOff_dst.append(rama)
		print "Rama Nombre: %s| carga_representativa: %s| Rama estado: %s| Rama flagtmp: %s | SubRedes: %s " %(rama.ramaFirewallNombre, rama.carga_representativa(), rama.estado, rama.flagtmp, rama.SubRedes)
	
	#Actualizamos las mediciones en cada SubRed
	dict_Flows = medirFlows_Ovs(ovs_intranet_DPID)
	for subred in arreglo_SubRedes :
		#values = [packet_count,byte_count,duration]
		values = dict_Flows.get(str(subred.ip_mask))
		subred.pps = (values[0] - subred.packetCount_old ) / (values[2] - subred.duration_old)
		subred.bps = (values[1] - subred.bytesConsumidos_old ) * 8 / (values[2] - subred.duration_old)
		subred.packetCount_old =  values[0]
		subred.bytesConsumidos_old = values[1]
		subred.duration_old = values[2]
		
		print "SubRed_Name: %s | key: %s | pps: %s | bps: %s " %(subred.nombre,subred.ip_mask,subred.pps,subred.bps)
	
	
	print time.time()

if __name__ == '__main__':
	#Creacion de Flow entries en funcion a sub-redes pre-establecidas
	crearFlowEntriesPorSubNet("subRedes")
	#sub_red_1 = SubRed('sub_red_1','192.168.1.0/255.255.255.224',0,0,0,0,0)
	#sub_red_2 = SubRed('sub_red_2','192.168.1.32/255.255.255.224',0,0,0,0,0)
	#print sub_red_1.nombre
	
	while 1 == 1:
		s.enter(2,1,accionCadaXSegundos,())
  		s.run()
	
	
