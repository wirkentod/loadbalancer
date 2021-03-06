import sys
import json
import csv
import sched
import time
import ast

from lib import StaticEntryPusher
from lib import RestApiFloodlight
from lib import RamaFirewall
from lib import SubRed
from lib import SessionActives

#iniciamos las variables globales

ip_controller = '10.20.10.8'
ip_server_collectorSession = '10.20.10.9'
ovs_intranet_DPID = "00:00:06:65:9b:78:cc:4f"
ovs_extranet_DPID = "00:00:f6:7b:24:5d:3e:4f"

#Definimos la interfaz en el ovs_intranet donde se reenviaran los paquetes para la busqueda de sesiones activas al servidor SessionServer
interfaz_puerto_sessions_actives = '3'
#Definimos las interfaces por defecto en caso los paquetes no pertenecen a ninguna subred
interfaz_default_ovs_intranet = '4'
interfaz_default_ovs_extranet = '1'

#Definimos las ramas correspondientes a cada Firewall
rama1 = RamaFirewall('8','7','1','rama1','NORMAL','ESTABLE',[])
rama2 = RamaFirewall('5','2','2','rama2','NORMAL','ESTABLE',[])
rama3 = RamaFirewall('6','6','3','rama3','NORMAL','ESTABLE',[])
#Rama Sensor Spare
rama4 = RamaFirewall('2','4','4','rama4','NORMAL','ESTABLE',[])

arreglo_ramas_Firewall = [rama1,rama2,rama3]
arreglo_SubRedes = []
#Posiblemente se eliminen estos dos arreglos
arreglo_rama_HandOff_src = []
arreglo_rama_HandOff_dst = []

umbral_HandOff = 1000 #bps

#Definimos los objetos que nos comunicaran con las interfaces REST
pusher = StaticEntryPusher(ip_controller)
sessionActives = SessionActives(ip_server_collectorSession)

def crearGroupEntriesPorRama():
	count = 1
	for rama in arreglo_ramas_Firewall:
		group_entry = {
			"switch" : ovs_intranet_DPID,
			"entry_type" : "group",
			"name" : "group-mod-" + str(count),
			"active" : "true",
			"group_type" : "all",
			"group_id" : str(count),
			"group_buckets" : [ 
				{
					"bucket_id" : "1",
					"bucket_watch_group" : "any",
					"bucket_actions":"output=" + str(rama.interfaz_puerto_ovs_intranet)
				},
				{
					"bucket_id" : "2", 
					"bucket_watch_group" : "any", 
					"bucket_actions" : "output=" + str(interfaz_puerto_sessions_actives)
				}
			]
			}
		count = count + 1
		pusher.set(group_entry)
		
def crearFlowEntriesPorSubNet(fileName):
	#Creamos los flow entries por defecto
	flow_Default_SubNet_intranet = {
			'switch':ovs_intranet_DPID,
			"name": "default_intranet",
			"cookie":"0",
			"priority":"0",
			"active":"true",
			"actions":"output=" + str(interfaz_default_ovs_intranet)
			}
	flow_Default_SubNet_extranet = {
			'switch':ovs_extranet_DPID,
			"name": "default_extranet",
			"cookie":"0",
			"priority":"0",
			"active":"true",
			"actions":"output=" + str(interfaz_default_ovs_extranet)
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
			"in_port":str(interfaz_default_ovs_intranet),
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
			"in_port":str(interfaz_default_ovs_extranet),
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

def change_mask(mask):
	if mask == "255.255.0.0":
		result = 16
	elif mask == "255.255.128.0":
		result = 17
	elif mask == "255.255.192.0":
		result = 18
	elif mask == "255.255.224.0":
		result = 19
	elif mask == "255.255.240.0":
		result = 20
	elif mask == "255.255.248.0":
		result = 21
	elif mask == "255.255.252.0":
		result = 22
	elif mask == "255.255.254.0":
		result = 23
	elif mask == "255.255.255.0":
		result = 24
	elif mask == "255.255.255.128":
		result = 25
	elif mask == "255.255.255.192":
		result = 26
	elif mask == "255.255.255.224":
		result = 27
	elif mask == "255.255.255.240":
		result = 28
	elif mask == "255.255.255.248":
		result = 29
	elif mask == "255.255.255.252":
		result = 30
	elif mask == "255.255.255.254":
		result = 31
		
	return str(result)
		
def ejecutarFlowEntriesSessionesActivas(rama,session_dict):
	time_insert = int(round(time.time()))
	for session in session_dict:
		ip_src = session.split("&")[0]
		ip_dst = session.split("&")[1]
		ip_proto = session.split("&")[2]
		sport = session.split("&")[3]
		dport = session.split("&")[4]
		
		if  int(ip_proto) == 6 :
			src_port = "tcp_src"
			dst_port = "tcp_dst"
		elif int(ip_proto) == 17:
			src_port = "udp_src"
			dst_port = "udp_dst"
			
		flow_session_intranet = {
			'switch':ovs_intranet_DPID,
			"name":str(time_insert) + session + "_intranet",
			"cookie":"0",
			"priority":"30",
			"eth_type ":"0x0800",
			"ipv4_src":str(ip_src),
			"ipv4_dst":str(ip_dst),
			"ip_proto":str(ip_proto),
			str(src_port):str(sport),
			str(dst_port):str(dport),
			"active":"true",
			"in_port":str(interfaz_default_ovs_intranet),
			"idle_timeout": "15",
			"actions":"output=" + str(rama.interfaz_puerto_ovs_intranet)
			}

		flow_session_extranet = {
			'switch':ovs_extranet_DPID,
			"name":str(time_insert) + session + "_extranet",
			"cookie":"0",
			"priority":"30",
			"eth_type ":"0x0800",
			"ipv4_dst":str(ip_src),
			"ipv4_src":str(ip_dst),
			"ip_proto":str(ip_proto),
			str(dst_port):str(sport),
			str(src_port):str(dport),
			"active":"true",
			"in_port":str(interfaz_default_ovs_extranet),
			"idle_timeout": "15",
			"actions":"output=" + str(rama.interfaz_puerto_ovs_extranet)
			}

		pusher.set(flow_session_intranet)
		pusher.set(flow_session_extranet)
		
#scheduler		
s = sched.scheduler(time.time, time.sleep)
def accionCadaXSegundos():
	
	ramas_HandOff_src_new = []
	ramas_HandOff_dst_new = []
	
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
	
	#Actualizamos las mediciones en cada Rama
	for rama in arreglo_ramas_Firewall:
		load_inst_puerto_intranet = medirBps_Ovs(rama.interfaz_puerto_ovs_intranet, 'tx', ovs_intranet_DPID)
		load_inst_puerto_extranet = medirBps_Ovs(rama.interfaz_puerto_ovs_extranet, 'tx', ovs_extranet_DPID)
		rama.carga_ovs_intranet = load_inst_puerto_intranet  
		rama.carga_ovs_extranet = load_inst_puerto_extranet
		carga_representativa = rama.carga_representativa()
		
		#Calcular promediador para comparar con el valor umbral
		delta = 0.8
                promediador = delta*float(rama.promediador_old) + (1 - delta)*float(carga_representativa)
                rama.promediador_old = promediador
                tiempo_carga = time.time()
		
		#Imprimimos los valores del promediador y la carga actual
                file_rama = open('./resultRamas/'+str(rama.ramaFirewallNombre)+'.csv', 'a')
                #file_rama.write('#|  X[n] - valor_representativo   |   Y[n] - promediador   |   Time    |' + '\n')
                file_rama.write(str(carga_representativa) + ',' + str(promediador) + ',' + str(tiempo_carga)    + '\n')
		
		#Si pasa el umbral
		if float(promediador) > float(umbral_HandOff):
			rama.flagtmp = 'INESTABLE'
			ramas_HandOff_src_new.append(rama)
			#if not rama in arreglo_rama_HandOff_src :
			#	arreglo_rama_HandOff_src.append(rama)
		else :
			rama.flagtmp = 'ESTABLE'
			ramas_HandOff_dst_new.append(rama)
			if rama.estado == 'CANDIDATA' and rama.flagtmp_old == 'INESTABLE':
				#Cambiamos la forma del prefijo a formato ip/num
				input = rama.SubRedHO.ip_mask
				res = input.split('/')
				output_prefix = res[0] + "/" + change_mask(res[1])
				subredparams = rama.SubRedHO.nombre + '&' + output_prefix
				#Se detiene la busqueda de sesiones activas
				rpta = sessionActives.stopSearch(subredparams)
				rama.estado = 'NORMAL'
		rama.flagtmp_old = rama.flagtmp
		#Si la rama esta en estado bloqueado
		if rama.estado == 'BLOQUEADO' :
			if rama.temp_bloqueado == 0:
				rama.estado = 'NORMAL'
			else:
				rama.temp_bloqueado = rama.temp_bloqueado - 1
		
		print "Rama Nombre: %s| carga_representativa: %s| Rama estado: %s| Rama flagtmp: %s | SubRedes: %s " %(rama.ramaFirewallNombre, rama.carga_representativa(), rama.estado, rama.flagtmp, rama.SubRedes)
	
	#Ordenamos los arreglos donde se almacenan las ramas 'ESTABLES' E 'INESTABLES' de forma descendente
	ramas_HandOff_src_new_descendente = sorted(ramas_HandOff_src_new, key=lambda rama: rama.carga_representativa(), reverse=True) 
	ramas_HandOff_dst_new_ascendente = sorted(ramas_HandOff_dst_new, key=lambda rama: rama.carga_representativa(), reverse=False)
	
	i = 0
	cantidad_ramas_HandOff_dst = len(ramas_HandOff_dst_new_ascendente)
	
	for rama in ramas_HandOff_src_new_descendente:
		if rama.estado != 'BLOQUEADO':
			if rama.estado == 'NORMAL' :
				#Buscamos la SubRed que mas se acomada para realizar el HandOff, ordenamos de manera ascendente
				SubRedes_ramas_ascendente = sorted(rama.SubRedes, key=lambda subred: subred.bps, reverse=False)
				#Escogemos la subred de menor carga para evitar el amortiguamiento del sistema
				sub_red_elegida = SubRedes_ramas_ascendente[0]
				rama.SubRedHO = sub_red_elegida
				#Cambiamos la forma del prefijo a formato ip/num
				input = sub_red_elegida.ip_mask
				res = input.split('/')
				output_prefix = res[0] + "/" + change_mask(res[1])
				subredparams = sub_red_elegida.nombre + '&' + output_prefix
				#Insertamos un Flow Entry para generar un port mirror de la SubRed correspondiente
				flow_mirror = {
						'switch':ovs_intranet_DPID,
						"name":str(sub_red_elegida.nombre) + "_mirror",
						"cookie":"0",
						"priority":"20",
						"eth_type ":"0x0800",
						"ipv4_src":sub_red_elegida.ip_mask,
						"active":"true",
						"in_port":str(interfaz_default_ovs_intranet),
						"hard_timeout": "15",
						"actions":"group=" + str(rama.groupID_ovs_intranet)
						}
				pusher.set(flow_mirror)
				#Empieza la recoleccion de las sesiones activas
				rpta = sessionActives.startCollection(subredparams)
				rama.estado = 'CANDIDATA'
				rama.timeHOsessions = time.time()
				#Observacion, Agregar a la clase RamaFirewall los siguietnes atributos: self.temp_HandOff y self.temp_bloqueado y self.SubRedHO, self.timeHOsessions
				#rama.temp_HandOff = 5
			elif rama.estado == 'CANDIDATA' :
				if time.time() - rama.timeHOsessions >= 15 :
				
					indice = i % cantidad_ramas_HandOff_dst
					
					input = rama.SubRedHO.ip_mask
					res = input.split('/')
					output_prefix = res[0] + "/" + change_mask(res[1])
					subredparams = rama.SubRedHO.nombre + '&' + output_prefix
					#query para importar informacion de las sesiones activas
					data = sessionActives.getSessions(subredparams)
					session_dict = ast.literal_eval(data)
					#Eliminamos el objeto que recolecta sesiones
					rpta = sessionActives.stopSearch(subredparams)
					
					#Ejecutamos las reglas de HandOff para las sesiones activas
					ejecutarFlowEntriesSessionesActivas(rama,session_dict)
					
					#Ejecutamos el HO de la subRED, escogemos el triplet
					#Triplet:
					Rama_src = rama
					#No se considera el caso cuando ramas_HandOff_dst_new_ascendente[] esta vacio
					#La eleccion del destino es en funcion al Round-Robin del arreglo ramas_HandOff_dst_new_ascendente 
					Rama_dst = ramas_HandOff_dst_new_ascendente[indice]
					Sub_red_HO = rama.SubRedHO
					
					#HandOff de sub-red a la Rama_dst
					flowSubNet_intranet = {
						'switch':ovs_intranet_DPID,
						"name":str(Sub_red_HO.nombre) + "_intranet",
						"cookie":"0",
						"priority":"10",
						"eth_type ":"0x0800",
						"ipv4_src":str(Sub_red_HO.ip_mask),
						"active":"true",
						"in_port":str(interfaz_default_ovs_intranet),
						"actions":"output=" + str(Rama_dst.interfaz_puerto_ovs_intranet)
						}

					flowSubNet_extranet = {
						'switch':ovs_extranet_DPID,
						"name":str(Sub_red_HO.nombre) + "_extranet",
						"cookie":"0",
						"priority":"10",
						"eth_type ":"0x0800",
						"ipv4_dst":str(Sub_red_HO.ip_mask),
						"active":"true",
						"in_port":str(interfaz_default_ovs_extranet),
						"actions":"output=" + str(Rama_dst.interfaz_puerto_ovs_extranet)
						}

					pusher.set(flowSubNet_intranet)
					pusher.set(flowSubNet_extranet)
					
					#Actualizamos las subredes de las ramas
					Rama_src.SubRedes.remove(Sub_red_HO)
					Rama_dst.SubRedes.append(Sub_red_HO)
					
					#Se BLOQUEA la rama
					rama.estado = 'BLOQUEADO'
					rama.temp_bloqueado = 5
					i = i + 1
				#else:

if __name__ == '__main__':
	#Creacion de Group entries para realizar forwarding multicast para recolectar las sesiones activas por Sub Red
	crearGroupEntriesPorRama()
	#Creacion de Flow entries en funcion a sub-redes pre-establecidas
	crearFlowEntriesPorSubNet("subRedes")
	#sub_red_1 = SubRed('sub_red_1','192.168.1.0/255.255.255.224',0,0,0,0,0)
	#sub_red_2 = SubRed('sub_red_2','192.168.1.32/255.255.255.224',0,0,0,0,0)
	#print sub_red_1.nombre
	
	while 1 == 1:
		s.enter(2,1,accionCadaXSegundos,())
  		s.run()
	
	
