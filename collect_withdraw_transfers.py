from config.app import AppConfig
import os
from lib.epiapi import epiapi
from pymongo import MongoClient
import logging, graypy

grayLogger = logging.getLogger('graylog')
grayLogger.setLevel(logging.CRITICAL)
handler = graypy.GELFHandler(os.environ['GRAYLOG_HOST'], int(os.environ['GRAYLOG_PORT']))
grayLogger.addHandler(handler)

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

config = AppConfig()

def isTransferCollected(id):
    total = db.preprocessing_withdraw_transfers.count_documents({'id': id})
    return total > 0

def insertWithdrawTransfer(accountId, transfer):
    # add owner account id
    transfer['accountId'] = accountId
    # inject status PENDING
    transfer['status'] = 'PENDING'
    newDoc = db.preprocessing_withdraw_transfers.insert_one(transfer)
    return newDoc

def process():
    # set large limit to get all transfers in one shot
    pageLimit = 9999
    totalSuccess = 0
    for accountId in config.withdraw['accounts']:
        status, transferRes = epiapiCli.get_transfers(accountId, pageLimit)

        # skip if status is not 200 OK
        if status != 200: continue
        
        transfers = transferRes['data']
        for transfer in transfers:
            if transfer['dest'][0:13] != 'paymentmethod': continue
            isCollected = isTransferCollected(transfer['id'])
            if not isCollected:
                insertedDoc = insertWithdrawTransfer(accountId, transfer)
                if insertedDoc is None:
                    grayLogger.critical('Could not insert transfer: {}'.format(transfer['id']), extra={'type': 'collect_epi_transfers', 'transfer': transfer})

if __name__ == '__main__':
    process()