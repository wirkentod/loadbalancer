import httplib
import json
 
class RestApiFloodlight(object):
 
    def __init__(self, server):
        self.server = server
 
    def measureLoad(self, ovsPid, port):
	path = '/wm/statistics/bandwidth/'+ ovsPid +'/'+ port +'/json'
        #print path
	headers = {
            'Content-type': 'application/json',
            'Accept': 'application/json',
        }
        body = json.dumps("")
        conn = httplib.HTTPConnection(self.server, 8080)
        conn.request('GET', path)
	#conn.request('GET', path, body, headers)
        response = conn.getresponse()
        ret = (response.status, response.reason, response.read())
        enviar = ret[2]
	#print ret[2]
        conn.close()
        return enviar

    def measureFlows(self, ovsPid):
	path = '/wm/core/switch/'+ ovsPid +'/flow/json'
        #print path
	headers = {
            'Content-type': 'application/json',
            'Accept': 'application/json',
        }
        body = json.dumps("")
        conn = httplib.HTTPConnection(self.server, 8080)
        conn.request('GET', path)
	#conn.request('GET', path, body, headers)
        response = conn.getresponse()
        ret = (response.status, response.reason, response.read())
        enviar = ret[2]
	#print ret[2]
        conn.close()
        return enviar

