import httplib
import json

class SessionActives(object):

	def __init__(self, server):
        	self.server = server
		
	def startCollection(self, prefix_subred):
		path = '/start?'+ prefix_subred
        	headers = {
			'Content-type': 'application/json',
			'Accept': 'application/json',
		}
		body = json.dumps("")
		conn = httplib.HTTPConnection(self.server, 8080)
		conn.request('GET', path)
		response = conn.getresponse()
		ret = (response.status, response.reason, response.read())
        	enviar = ret[2]
		#print ret[2]
        	conn.close()
        	return enviar
	
	def getSessions(self, prefix_subred):
		path = '/give?'+ prefix_subred
        	headers = {
			'Content-type': 'application/json',
			'Accept': 'application/json',
		}
		body = json.dumps("")
		conn = httplib.HTTPConnection(self.server, 8080)
		conn.request('GET', path)
		response = conn.getresponse()
		ret = (response.status, response.reason, response.read())
        	enviar = ret[2]
		conn.close()
        	return enviar
		
	def stopSearch(self, prefix_subred):
		path = '/kill?'+ prefix_subred
        	headers = {
			'Content-type': 'application/json',
			'Accept': 'application/json',
		}
		body = json.dumps("")
		conn = httplib.HTTPConnection(self.server, 8080)
		conn.request('GET', path)
		response = conn.getresponse()
		ret = (response.status, response.reason, response.read())
        	enviar = ret[2]
		conn.close()
        	return enviar
		
		
		
		
		
		
