import sys
import json
import csv
import sched
import time
#from lib import Project
#from lib import Options
from lib import StaticEntryPusher
from lib import RestApiFloodlight
from lib import PuertoFirewall

#iniciamos las variables globales

ip_controller = '10.20.10.26'
ovs_intranet_DPID = "00:00:5a:9d:cb:0b:01:4b"
ovs_extranet_DPID = "00:00:d2:d8:cc:51:e3:4f"

#Definimos los puertos correspondientes a cada Firewall
sensor1 = PuertoFirewall('6','3','sensor1')
sensor2 = PuertoFirewall('5','6','sensor2')
sensor3 = PuertoFirewall('3','1','sensor3')
#Sensor Spare
sensor4 = PuertoFirewall('7','5','sensor4')
arreglo_puertos_Firewall = [sensor1,sensor2,sensor3]
arreglo_puerto_elegido_HandOff = []
arreglo_puerto_elegido_enProceso_HandOff = []

#Definimos los diccionarios donde se guardan el historial de carga de cada puerto de los ovs
#dict_load_net = {'sensor1':[], 'sensor2':[], 'sensor3':[]}
dict_load_intranet = {}
dict_load_extranet = {}
for puerto in arreglo_puertos_Firewall:
	dict_load_intranet[str(puerto.puertoFirewallNombre)] = []
	dict_load_extranet[str(puerto.puertoFirewallNombre)] = []
#Definimos los valores umbrales
umbral_HandOff = 26100 #bps


#pusher = StaticEntryPusher(ip_controller)

def crearFlowEntriesPorSubNet(fileName):
	#Cargamos las subnet en el diccionario subRedes = {"subRedName":"prefijo"}
	#pusher = StaticEntryPusher(ip_controller)
	subRedes = {}
	i = 0
	cantidadFirewalls = len(arreglo_puertos_Firewall)
	for subRedName, prefijo in csv.reader(open('./subnets/'+str(fileName)+'.csv')):
		indice = i % cantidadFirewalls
		subRedes[str(subRedName)] = str(prefijo)
		flowSubNet_intranet = {
			"switch":ovs_intranet_DPID,
			"name":str(subRedName),
			"priority":"10",
			"eth_type ":"0x0800",
			"ipv4_src":str(prefijo),
			"active":"true",
			"actions":"output=" + str(arreglo_puertos_Firewall[indice].interfaz_puerto_ovs_intranet)
		}
	   
		flowSubNet_extranet = {
			"switch":ovs_extranet_DPID,
			"name":str(subRedName),
			"priority":"10",
			"eth_type ":"0x0800",
			"ipv4_dst":str(prefijo),
			"active":"true",
			"actions":"output=" + str(arreglo_puertos_Firewall[indice].interfaz_puerto_ovs_extranet)
		}
		#pusher.set(flowSubNet_intranet)
		pusher.set(flowSubNet_extranet)
		pusher.set(flowSubNet_intranet)
		i = i + 1	

def medirBps_Ovs(puerto, direction, ovs_PID):
	rest = RestApiFloodlight(ip_controller)
	data = rest.measureLoad(ovs_PID, str(puerto))
	j = json.loads(data)
	key = 'bits-per-second-' + direction
	return j[0][str(key)]

def guardarInformacionDicts_Load_Net():
	for puerto in arreglo_puertos_Firewall:
                load_inst_puerto_intranet = medirBps_Ovs(puerto.interfaz_puerto_ovs_intranet, 'tx', ovs_intranet_DPID)
                puerto.carga_ovs_intranet = load_inst_puerto_intranet
                dict_load_intranet[str(puerto.puertoFirewallNombre)].append(float(load_inst_puerto_intranet))
               
#definimos el trigerTime 1
s = sched.scheduler(time.time, time.sleep)

#logsLoadSensors = sched.scheduler(time.time, time.sleep)

def accionCadaXSegundos():
	
	#Definimos los posibles puertos en estado HandOff
	posible_puerto_HandOff = []
	
	for puerto in arreglo_puertos_Firewall:
		load_inst_puerto_intranet = medirBps_Ovs(puerto.interfaz_puerto_ovs_intranet, 'tx', ovs_intranet_DPID)
		load_inst_puerto_extranet = medirBps_Ovs(puerto.interfaz_puerto_ovs_extranet, 'tx', ovs_extranet_DPID)
		puerto.carga_ovs_intranet = load_inst_puerto_intranet  
		puerto.carga_ovs_extranet = load_inst_puerto_extranet
		carga_representativa = puerto.carga_representativa()
		
		if float(carga_representativa) > float(umbral_HandOff):
			posible_puerto_HandOff.append(puerto)
	
	#Si un puerto en proceso HandOff no supera el umbral se procede a eliminar el evento Comenzar_Evento_HandOff
	if arreglo_puerto_elegido_enProceso_HandOff != [] :
		for puerto in arreglo_puerto_elegido_enProceso_HandOff :
			if not puerto in posible_puerto_HandOff :
				print "Eliminamos el proceso HandOff correspondiente al puerto : %s" %(puerto.puertoFirewallNombre)	
	
	#Analisis de los posibles puertos que ingresan al Evento Comenzar_Evento_HandOff
	if len(posible_puerto_HandOff) == len(arreglo_puertos_Firewall) :
		print "Ingresar  FWs, todos estan ocupados"
		i = 1
	elif len(posible_puerto_HandOff) == 0 :
		print "No se encuentra algun puerto que supere el umbral"
		j = 1
	else :
		#Sort de arreglo de forma descendente
		arreglo_ordenador_por_carga_descendente = sorted(posible_puerto_HandOff, key=lambda puerto: puerto.carga_representativa(), reverse=True) 
		for puerto in arreglo_ordenador_por_carga_descendente:
			if not puerto in arreglo_puerto_elegido_enProceso_HandOff :
				puertoElegido_HandOff = puerto
				#Comenzar_Evento_HandOff(puertoElegido_HandOff)
				arreglo_puerto_elegido_enProceso_HandOff.append(puertoElegido_HandOff)
				print puertoElegido_HandOff.puertoFirewallNombre
				break	
	


		#print "p_intranet: %s | p_extranet: %s | carga_representativa: %s" %(load_inst_puerto_intranet,load_inst_puerto_extranet,carga_representativa)
		#dict_load_intranet[str(puerto.puertoFirewallNombre)].append(float(load_inst_puerto_intranet))
		#print puerto.carga_ovs_intranet
	print "---------------------------------"
	print "posible_puerto_HandOff: "
	for puerto in posible_puerto_HandOff:
		print "puerto Nombre: %s| carga_ovs_intranet: %s| carga_ovs_extranet: %s| carga_representaiva: %s " %(puerto.puertoFirewallNombre, puerto.carga_ovs_intranet, puerto.carga_ovs_extranet, puerto.carga_representativa())
	print "arreglo_puerto_elegido_enProceso_HandOff:"
	for puerto in arreglo_puerto_elegido_enProceso_HandOff:
                print "puerto Nombre: %s| carga_ovs_intranet: %s| carga_ovs_extranet: %s| carga_representaiva: %s " %(puerto.puertoFirewallNombre, puerto.carga_ovs_intranet, puerto.carga_ovs_extranet, puerto.carga_representativa())
	
	#print dict_load_intranet

if __name__ == '__main__':

	#Se crean flow entries en funcion a las subRedes que hay en el archivo = subRedes.csv
	#crearFlowEntriesPorSubNet("subRedes")
	print "hola2"
	mide = medirBps_Ovs(3, 'tx', '00:00:5a:9d:cb:0b:01:4b')
	print mide
	#while 1 == 1:
	#	s.enter(3,1,accionCadaXSegundos,())
  		#s.enter(20,1,guardarInformacionDicts_Load_Net,())
	#	s.run()
		    	


	#puerto = '2'
	#load = medirBps_Ovs(puerto, 'tx', ovs_intranet_DPID)
	#print "load:"
	#print load

	"""pusher = StaticEntryPusher(ip_controller)
	flowSubNet_intranet = {
		"switch":"00:00:96:a6:c9:d8:d2:40",
		"name":"subred1",
		"priority":"10",
		"eth_type ":"0x0800",
		"ipv4_src":"192.168.1.0/27",
		"active":"true",
		"actions":"output=5" 
	}
		
	flowSubNet_extranet = {
		"switch":"00:00:ce:19:09:f9:17:40",
		"name":"subred1",
		"priority":"10",
		"eth_type ":"0x0800",
		"ipv4_dst":"192.168.1.0/27",
		"active":"true",
		"actions":"output=3" 
	}"""
	
	#pusher.set(flowSubNet_intranet)
	#pusher.set(flowSubNet_extranet)

	
	
	#for puerto in arreglo_puertos_Firewall:
	#	print puerto.interfaz_puerto_ovs_intranet
	
	
	"""pusher = StaticEntryPusher(ip_controller)
	
	flowSubNet1 = {
    		'switch':ovs_intranet_DPID,
    		"name":"flow_subnet_1",
    		"priority":"10",
		"eth_type ":"0x0800",
    		"ipv4_src":"192.168.3.0/27",
    		"active":"true",
    		"actions":"output=6"
    	}"""
	

	#rest = RestApiFloodlight(ip_controller)
	#data = rest.measureLoad(ovs_intranet_DPID, str(2))
	#j = json.loads(data)
	#print j[0]['bits-per-second-tx']
	
	#print "Entra:"
	#print str(data)
	#pusher.remove(flowSubNet1)
	
	#pusher.set(flowEntry1) 
	#pusher.remove(flow1)
	#pusher.set(flow1)
	#pusher.set(flow2)
	
	
