import os, json
from requests import request


class vba(object):
    def __init__(self):
        self.api_url = os.environ['VBA_SERVICE_URL']

    def authenticate_request(func):
        def wrap(self, *args, **kwargs):
            url, method, body = func(self, *args, **kwargs)
            headers = {
                'Content-Type': 'application/json'
            }
            resp = request(method=method, url=url, params={}, data=(json.dumps(body) if body != '' else None), json=None, headers=headers)
            return resp.status_code, resp.content
        return wrap

    @authenticate_request
    def addFunds(self, amount, message, sourceCurrency, destCurrency):
        url = self.api_url + '/add-funds/synapse'
        method = 'POST'
        body = {
            'amount': amount,
            'message': message,
            'sourceCurrency': sourceCurrency,
            'destCurrency': destCurrency,
        }
        print(body)
        return url, method, body
