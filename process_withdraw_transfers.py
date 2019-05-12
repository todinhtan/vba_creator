import os, json
from pymongo import MongoClient
import logging, graypy
from lib.wyre import wyre

grayLogger = logging.getLogger('graylog')
grayLogger.setLevel(logging.CRITICAL)
handler = graypy.GELFHandler(os.environ['GRAYLOG_HOST'], int(os.environ['GRAYLOG_PORT']))
grayLogger.addHandler(handler)

mongoClient = MongoClient(os.environ['VBA_DB_HOST'], int(os.environ['VBA_DB_PORT']))
db = mongoClient.vba_service

def createWyreApi(credentials):
    account_id = credentials.get('accountId', None)
    api_key = credentials.get('apiKey', None)
    secret_key = credentials.get('apiSecKey', None)
    return wyre(account_id, 'v3', api_key, secret_key)

wyreCli = createWyreApi({
    "accountId": os.environ['WYRE_ADMIN_ACCOUNTID'],
    "apiKey": os.environ['WYRE_ADMIN_APIKEY'],
    "apiSecKey": os.environ['WYRE_ADMIN_SECRET']
})

def getPendingWithdraw():
    transfers = db.daily_withdraw_transfers.find({'status': 'PENDING'})
    for transfer in transfers:
        yield transfer

def markDoneWithdraw(_id, mainTransferResp = None, feeTransferResp = None):
    db.daily_withdraw_transfers.update({'_id':_id}, {'$set':{'status':'DONE', 'mainTransferResp': mainTransferResp, 'feeTransferResp': feeTransferResp}})

def process():
    for transfer in getPendingWithdraw():
        # main transfer
        payload = {
            'source': transfer.get('source'),
            'dest': transfer.get('dest'),
            'destAmount': transfer.get('destAmount'),
            'callbackUrl': transfer.get('callbackUrl'),
            'message': transfer.get('message'),
            'sourceCurrency': transfer.get('sourceCurrency'),
            'destCurrency' : transfer.get('destCurrency'),
        }
        status, resp = wyreCli.createTransfer(payload)
        feeResp = None
        if status == 200:
            # fee transfer
            fee = transfer.get('fee')
            if fee <= 0:
                print('Transfer {}: fee is not greater than zero'.format(transfer.get('id')))
            else:
                feePayload = {
                    'source': transfer.get('source'),
                    'dest': transfer.get('feeDest'),
                    'destAmount': fee,
                    'message': transfer.get('message'),
                    'sourceCurrency': transfer.get('sourceCurrency'),
                    'destCurrency' : transfer.get('destCurrency')
                }
                feeStatus, feeResp = wyreCli.createTransfer(feePayload)
                if feeStatus != 200: print('Error while create fee transfer: ' + json.dumps(feeResp))
        else:
            print('Error while create main transfer: ' + json.dumps(resp))
        markDoneWithdraw(transfer.get('_id'), resp, feeResp)

if __name__ == '__main__':
    process()
