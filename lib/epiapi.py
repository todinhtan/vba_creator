import time
from synapse_pay_rest.models.nodes import *
import json
import hmac
import os
from requests import request


class epiapi(object):
    def __init__(self, account_id, api_version, api_key, api_secret):
        self.account_id = account_id
        self.api_url = '{}/{}'.format(os.environ['EPIAPI_BASE_URL'],api_version)
        self.api_version = api_version
        self.api_key = api_key
        self.api_secret = api_secret

    #authentication decorator. May raise ValueError if no json content is returned

    def authenticate_request(func):
        def wrap(self, *args, **kwargs):
            url, method, body = func(self, *args, **kwargs)
            params = {}
            timestamp = int(time.time() * 1000)
            url += '?timestamp={}'.format(timestamp)
            bodyJson = json.dumps(body) if body != '' else ''
            headers = {}
            headers['Content-Type'] = 'application/json'
            headers['X-Api-Version'] = self.api_version
            headers['X-Api-Key'] = self.api_key
            headers['X-Api-Signature'] = hmac.new(self.api_secret.encode('utf-8'), (url + bodyJson).encode('utf-8'), 'SHA256').hexdigest()
            print(headers['X-Api-Signature'])
            resp = request(method=method, url=url, params=params, data=(json.dumps(body) if body != '' else None), json=None, headers=headers)
            if resp.text is not None: #Wyre will always try to give an err body
                return resp.status_code, resp.json()
            return 404, {}
        return wrap

    def authenticate_session(func):
        def wrap(self, *args, **kwargs):
            url, method, body, sessionId = func(self, *args, **kwargs)
            params = {}
            timestamp = int(time.time() * 1000)
            url += '?timestamp={}'.format(timestamp)
            if sessionId is not None:
                url += '&sessionId={}'.format(sessionId)
            print(url)
            resp = request(method=method, url=url, params=params, data=None, json=None)
            if resp.content is not None: #Wyre will always try to give an err body
                return resp.status_code, resp.content
            return 404, {}
        return wrap

    def authenticate_request2(func):
        def wrap(self, *args, **kwargs):
            url, method, body = func(self, *args, **kwargs)
            params = {}
            timestamp = int(time.time() * 1000)
            url += '?timestamp={}'.format(timestamp)
            print(url)
            headers = {}
            headers['X-Api-Version'] = self.api_version
            headers['X-Api-Key'] = self.api_key
            headers['X-Api-Signature'] = hmac.new(self.api_secret.encode('utf-8'), url.encode('utf-8'), 'SHA256').hexdigest()
            print(headers['X-Api-Signature'])
            resp = request(method=method, url=url, params=params, data=None, json=None, headers=headers)
            if resp.text is not None: #Wyre will always try to give an err body
                return resp.status_code, resp.content
            return 404, {}
        return wrap

    def authenticate_request3(func):
        def wrap(self, *args, **kwargs):
            url, method, body = func(self, *args, **kwargs)
            params = {}
            timestamp = int(time.time() * 1000)
            url += '&timestamp={}'.format(timestamp)
            print(url)
            headers = {}
            headers['Content-Type'] = 'image/png'
            headers['X-Api-Version'] = self.api_version
            headers['X-Api-Key'] = self.api_key
            headers['X-Api-Signature'] = hmac.new(self.api_secret.encode('utf-8'), url.encode('utf-8') + body, 'SHA256').hexdigest()
            print(headers['X-Api-Signature'])
            resp = request(method=method, url=url, params=params, data=(body if body != '' else None), json=None, headers=headers)
            if resp.text is not None: #Wyre will always try to give an err body
                return resp.status_code, resp.json()
            return 404, {}
        return wrap

    @authenticate_request
    def get_wallet(self, walletId):
        url = self.api_url + '/wallet/' + walletId
        method = 'GET'
        body = ''
        return url, method, body

    @authenticate_request
    def update_wallet(self, walletId, vbaData):
        url = self.api_url + '/wallet/' + walletId
        method = 'POST'
        body = {"vbaData":vbaData}
        return url, method, body

    @authenticate_request
    def update_wallet_status(self, walletId, status, reason = ''):
        url = "%s/wallet/%s/status" % (self.api_url, walletId)
        print(url)
        method = 'POST'
        body = { "status":status, reason:reason }
        return url, method, body

    @authenticate_request
    def get_govid(self, idDoc):
        # {{host}}/v2/documents?ownerSrn={{authenticatedAs}}&sessionId={{sessionId}}
        url = idDoc if "http" in idDoc else (self.api_url + '/document/' + idDoc)
        print(url)
        method = 'GET'
        body = ''
        return url, method, body

    @authenticate_request
    def get_coi(self, coiDoc):
        url = coiDoc if "http" in coiDoc else (self.api_url + '/document/' + coiDoc)
        # url = "http://sino-us.com/UploadFiles/2013/5/30/201305301045590301.jpg"
        print(url)
        method = 'GET'
        body = ''
        return url, method, body

    @authenticate_request3
    def upload_doc(self):
        url = self.api_url + '/documents?ownerSrn=' + walletSrn
        method = 'POST'
        body = docImage
        return url, method, body
