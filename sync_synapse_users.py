from synapse_pay_rest.models.nodes import *
from synapse_pay_rest import User
from synapse_pay_rest import Client
from synapse_pay_rest import Node
from synapse_pay_rest import Subnet
import graypy
import threading
import logging
import json, os
from requests import get
from pymongo import MongoClient

grayLogger = logging.getLogger('graylog')
grayLogger.setLevel(logging.CRITICAL)
handler = graypy.GELFHandler(os.environ['GRAYLOG_HOST'], int(os.environ['GRAYLOG_PORT']))
grayLogger.addHandler(handler)

mongoClient = MongoClient('13.229.119.114', 27017)
db = mongoClient.vba_service

myip = get('https://api.ipify.org').text
args = {
    'client_id': os.environ['SYNAPSE_LIVE_ID'], # your client id
    'client_secret': os.environ['SYNAPSE_LIVE_SECRET'], # your client secret
    'fingerprint': '5af084654688ae0043d84603',
    'ip_address': myip, # user's IP
    'development_mode': False if os.environ['SYNAPSE_ENV'] == 'production' else True, # (optional) default False
    # 'logging': bool(os.environ['ON_DEBUG']) # (optional) default False # (optional) logs to stdout if True
}

client = Client(**args)

def getWalletsHaveUserId(collection):
    wallets = collection.find({'country': 'US', 'vbaData.userId' : { '$exists': True, '$ne': None }})
    for doc in wallets:
        yield doc

# def saveSynapseUser(collection):

def process():
    for wallet in getWalletsHaveUserId(db.vbarequests):
        userId = wallet.get('vbaData').get('userId')
        walletId = wallet.get('walletId')
        user = User.by_id(client, userId, 'yes')
        userInfo = user.__getattribute__('json')

        # append walletId
        userInfo['walletId'] = walletId

        # rename mongo reserved keys
        userInfo['userId'] = userInfo.pop('_id')

        if userInfo is not None:
            db.synapse_users.update({'walletId':walletId}, {'$set': userInfo}, upsert = True)
        else:
            grayLogger.critical('user not found', extra={'type': 'sync_synapse_users', 'userId': userId})
            print('user not found by id: {}'.format(userId))

if __name__ == '__main__':
    process()