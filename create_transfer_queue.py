from lib.wyre import wyre
import logging, graypy
import os, json
import threading
from requests import get
from pymongo import MongoClient
from lib.vba import vba
# GRAYLOG_HOST=3.1.25.26 GRAYLOG_PORT=12202 WYRE_ADMIN_ACCOUNTID=AC-T8DT7YJEAP7 WYRE_ADMIN_APIKEY=AK-67N6BTRD-WVEUCPTU-93QF4MZQ-VJBV3MAE WYRE_ADMIN_SECRET=SK-ANPR7NW9-TVVZZT3V-DGXVNU33-22HD2Q67 WYRE_BASE_URL=https://api.testwyre.com VBA_SERVICE_URL=https://vba.epiapi.com python3 create_transfer_queue.py
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

vbaCli = vba()

def getWalletIdByUserId(userId):
    vba = db.vbarequests.find_one({'country': 'US', 'vbaData.userId': userId})
    return vba.get('walletId') if vba is not None else None

def insertQueuedTranfer(document):
    newDoc = db.daily_topup_transfers.insert_one(document)
    return newDoc

def isQueuedTranferExisted(wyreTransferId):
    total = db.daily_topup_transfers.count_documents({'wyreTransferId': wyreTransferId})
    return total > 0

def process():
    threading.Timer(60, process).start()
    http_code, trans_info = wyreCli.get_trans_info()
    if http_code == 200:
        transfers = trans_info['data']
        if transfers is not None and len(transfers) > 0:
            for transfer in transfers:
                # skip if source != 'service:Fiat Credits'
                if transfer['source'] != 'service:Fiat Credits':
                    continue

                # skip if status != 'COMPLETED'
                if transfer['status'] != 'COMPLETED':
                    continue

                # skip if sourceAmount != destAmount
                if transfer['sourceAmount'] != transfer['destAmount']:
                    continue

                transferId = transfer['id']
                # skip if it has been added to queue
                if isQueuedTranferExisted(transferId):
                    continue

                # hardcode message = userId
                message = transfer['message']
                # message = '5c9afc555ac64800661b190a'
                if message is None or message == '':
                    continue
                
                # http_status, response = vbaCli.addFunds(transfer['sourceAmount'], message, transfer['sourceCurrency'], transfer['destCurrency'])
                # newTransfer = json.loads(response)
                walletId = getWalletIdByUserId(message)
                if walletId is None:
                    continue
                
                document = {
                    # 'transferId': newTransfer['transfer']['id'],
                    'wyreTransferId': transfer['id'],
                    'source': transfer['source'],
                    'sourceCurrency': transfer['sourceCurrency'],
                    'destCurrency': transfer['destCurrency'],
                    'sourceAmount': transfer['sourceAmount'],
                    'destAmount': transfer['destAmount'],
                    'dest': 'wallet:{}'.format(walletId),
                    'userId': message,
                    'message': 'addenda',
                    'autoConfirm': True,
                    'status': 'PENDING'
                }
                insertQueuedTranfer(document)

if __name__ == '__main__':
    process()
