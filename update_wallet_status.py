from requests import request
import os
from pymongo import MongoClient
import threading
from lib.epiapi import epiapi

mongoClient = MongoClient(os.environ['VBA_DB_HOST'], int(os.environ['VBA_DB_PORT']))
db = mongoClient.vba_service


def createEpiApi(credentials):
    account_id = credentials.get('accountId', None)
    api_key = credentials.get('apiKey', None)
    secret_key = credentials.get('apiSecKey', None)
    return epiapi(account_id, 'v2', api_key, secret_key)

epiapiCli = createEpiApi({
    "accountId": os.environ['EPIAPI_ADMIN_ACCOUNTID'],
    "apiKey": os.environ['EPIAPI_ADMIN_APIKEY'],
    "apiSecKey": os.environ['EPIAPI_ADMIN_SECRET']
})

def getNotExecutedRequests(collection):
    vbaRequests = collection.find({'$or':[{'status':'WAITING_FOR_APPROVAL'},{'status':'APPROVED'}] ,'vbaData.accountNum': {'$exists': True}, 'callbackStatus': {'$exists': False}, 'sessionId': {'$exists': True, '$ne': None}})
    for req in vbaRequests:
        yield req

def updateStatusApproved(walletId):
    # headers = {}
    # headers['Content-Type'] = 'application/json'
    # body = { 'status': 'APPROVED' }
    # endpoint = "%s/wallet/%s/status?sessionId=%s" % (apiUrl, walletId, sessionId)
    # # params = { 'sessionId': sessionId }
    # print ("endpoint %s" % (endpoint))
    # resp = request(method='POST', url=endpoint, data=(json.dumps(body) if body != '' else None), json=None, headers=headers)
    http_status, info = epiapiCli.update_wallet_status(walletId, 'APPROVED')
    return http_status, info

def updateCallbackStatus(walletId, collection, status):
    collection.update_many({'walletId': walletId}, {'$set': {'callbackStatus':status}})


def process():
    threading.Timer(60, process).start()
    print('checkWalletStatusProcess')
    for req in getNotExecutedRequests(db.vbarequests):
        walletId = req.get('walletId')
        print(walletId)
        httpCode, body = updateStatusApproved(walletId)
        print(httpCode)
        if (httpCode == 204 or httpCode == 200):
            updateCallbackStatus(walletId, db.vbarequests, "executed")
        elif (httpCode == 401):
            updateCallbackStatus(walletId, db.vbarequests, "unauthorized")


if __name__ == '__main__':
    process()
