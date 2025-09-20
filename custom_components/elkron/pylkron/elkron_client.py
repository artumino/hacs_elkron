import requests
import hashlib
import time
import uuid

class ElkronClient:
    def __init__(self, username, password, host):
        self.username = username
        self.password = self.computeDoubleMd5(password)
        self.host = host
        self.baseAddress = 'http://' + host + '/'
        self.sessionCookie = {'TRACKID': 'aea43f1442f9dcde125cffbcd1508311', 'i18next':'it'}

    def computeDoubleMd5(self, password):
        hasher1 = hashlib.md5(password.encode('utf-8'))
        hasher2 = hashlib.md5(hasher1.hexdigest().encode('utf-8'))
        return hasher2.hexdigest()

    def printInfo(self):
        print(self.username)
        print(self.password)


    def getSysInfo(self):
        r = requests.get(self.baseAddress + 'sys/info.cgi', {'_': int(time.time())}, cookies=self.sessionCookie)
        if r.ok:
            response = r.json()
            if response and response['data']:
                return response['data']
        raise ConnectionError('Could not connect to host to get system infos')

    def getUserInfo(self):
        r = requests.get(self.baseAddress + 'user/info.cgi', {'_': int(time.time())}, cookies=self.sessionCookie)
        if r.ok:
            response = r.json()
            if response and response['data']:
                return response['data']
        raise ConnectionError('Could not connect to host to get user infos')

    def isLoggedIn(self):
        r = requests.get(self.baseAddress + 'user/refresh.cgi', {'_': int(time.time())}, cookies=self.sessionCookie)
        return r.ok and r.status_code != 400 and r.status_code != 405

    def getPlantStructure(self):
        r = requests.get(self.baseAddress + 'spweco/plantstructure.cgi', {'_': int(time.time())}, cookies=self.sessionCookie)
        if r.ok and r.status_code != 400 and r.status_code != 405:
            response = r.json()
            if response['result'] == 'ACK':
                return response['data']
        raise ConnectionRefusedError('Login expired')

    def getGlobalStates(self):
        r = requests.get(self.baseAddress + 'spweco/globalstates.cgi', {'_': int(time.time())}, cookies=self.sessionCookie)
        if r.ok and r.status_code != 400 and r.status_code != 405:
            response = r.json()
            if response['result'] == 'ACK':
                return response['data']
        raise ConnectionRefusedError('Login expired')

    def getDetailedStates(self):
        r = requests.get(self.baseAddress + 'spweco/detailedstates.cgi', {'_': int(time.time())}, cookies=self.sessionCookie)
        if r.ok and r.status_code != 400 and r.status_code != 405:
            response = r.json()
            if response['result'] == 'ACK':
                return response['data']
        raise ConnectionRefusedError('Login expired')

    def getShortcuts(self):
        r = requests.get(self.baseAddress + 'spweco/getshortcuts.cgi', {'_': int(time.time())}, cookies=self.sessionCookie)
        if r.ok and r.status_code != 400 and r.status_code != 405:
            response = r.json()
            if response['result'] == 'ACK':
                return response['data']
        raise ConnectionRefusedError('Login expired')

    def getFilteredStructure(self):
        r = requests.get(self.baseAddress + 'spweco/filteredstructure.cgi', {'_': int(time.time())}, cookies=self.sessionCookie)
        if r.ok and r.status_code != 400 and r.status_code != 405:
            response = r.json()
            if response['result'] == 'ACK':
                return response['data']
        raise ConnectionRefusedError('Login expired')


    def doLogin(self):
        if self.isLoggedIn():
            return True

        p = requests.post(self.baseAddress + 'user/login.cgi', None, {'user': self.username, 'pwd':self.password}, cookies=self.sessionCookie)
        if p.ok and p.status_code != 400 and p.status_code != 405:
            response = p.json()
            if response['result'] == 'ACK':
                return response['data']
            else:
                raise ConnectionRefusedError('Invalid login parameters')
        
        raise ConnectionRefusedError('Cannot contact the login endpoint')
        
    def doLogout(self):
        p = requests.post(self.baseAddress + 'user/logout.cgi', None, cookies=self.sessionCookie)
        if p.ok and p.status_code != 400 and p.status_code != 405:
            response = p.json()
            if response['result']:
                return response['result'] == 'ACK'
        return False

    def doAccess(self, code):
        p = requests.post(self.baseAddress + 'spweco/access.cgi', None, {'code': code}, cookies=self.sessionCookie)
        if p.ok:
            response = p.json()
            if response['result'] == 'ACK':
                return True
            else:
                return False
        
        raise ConnectionRefusedError('Cannot contact the access endpoint')

    def doActivateZones(self, zoneIds):
        p = requests.post(self.baseAddress + 'spweco/activate.cgi', None, {'zone': zoneIds}, cookies=self.sessionCookie)
        if p.ok and p.status_code != 400 and p.status_code != 405:
            response = p.json()
            if response['result'] == 'ACK':
                return response
            else:
                raise ConnectionRefusedError('User not authenticated or Zone undefined')
        
        raise ConnectionRefusedError('Cannot contact the activation endpoint')

    def doDeactivateZones(self, zoneIds):
        p = requests.post(self.baseAddress + 'spweco/deactivate.cgi', None, {'zone': zoneIds}, cookies=self.sessionCookie)
        if p.ok and p.status_code != 400 and p.status_code != 405:
            response = p.json()
            if response['result'] == 'ACK':
                return response
            else:
                raise ConnectionRefusedError('User not authenticated or Zone undefined')
        
        raise ConnectionRefusedError('Cannot contact the activation endpoint')

    def doActivate(self, code, zoneIds):
        if not self.doAccess(code):
            raise ConnectionRefusedError("Invalid code!")
        data = self.doActivateZones(zoneIds)

        #If this one logs in then logout
        if self.getUserInfo()['userid'] != -1:
           self.doAccess(code)

        return data

    def doDeactivate(self, code, zoneIds):
        if not self.doAccess(code):
            raise ConnectionRefusedError("Invalid code!")
            
        data = self.doDeactivateZones(zoneIds)

        #If this one logs in then logout
        if self.getUserInfo()['userid'] != -1:
           self.doAccess(code)

        return data
