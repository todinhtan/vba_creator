from synapse_pay_rest.models.nodes import *
from synapse_pay_rest import User
from synapse_pay_rest import Client
from synapse_pay_rest import Node
from synapse_pay_rest import Subnet
import os
from requests import get
from pymongo import MongoClient

mongoClient = MongoClient(os.environ['VBA_DB_HOST'], int(os.environ['VBA_DB_PORT']))
db = mongoClient.vba_service

myip = get('https://api.ipify.org').text
args = {
    'client_id': os.environ['SYNAPSE_LIVE_ID'], # your client id
    'client_secret': os.environ['SYNAPSE_LIVE_SECRET'], # your client secret
    'fingerprint': '5af084654688ae0043d84603',
    'ip_address': myip, # user's IP
    'development_mode': False if os.environ['SYNAPSE_ENV'] == 'production' else True, # (optional) default False
    'logging': False # (optional) default False # (optional) logs to stdout if True
}

client = Client(**args)

def getPendingDoc(collection):
    docs = collection.find({'status': 'PENDING'})
    for doc in docs:
        yield doc

def markDoneDoc(collection, userId):
    collection.update({'userId':userId}, {'$set':{'status':'DONE'}})

def markDel(userId, status):
    db.vbarequests.update({'vbaData.userId':userId}, {'$set':{'status':status}})

def process():
    for pendingDeactiveNode in getPendingDoc(db.deactive_nodes):
        userId = pendingDeactiveNode.get('userId')
        if userId is not None:
            user = User.by_id(client, userId, 'yes')
            nodes = Node.all(user)
            for node in nodes:
                client.nodes.delete(userId, node.id)

            # set to DONE
            markDel(userId,'LOCKED-USER')
            markDoneDoc(db.deactive_nodes, userId)

    for pendingDeactiveNode in getPendingDoc(db.lock_users):
        userId = pendingDeactiveNode.get('userId')
        if userId is not None:
            user = User.by_id(client, userId, 'yes')
            if user.permission != 'MAKE-IT-GO-AWAY':
                payload = {
                    'permission': 'MAKE-IT-GO-AWAY'
                }
                client.users.update(userId, payload)

            # set to DONE
            markDel(userId,'DEACTIVATED-NODE')
            markDoneDoc(db.lock_users, userId)

if __name__ == '__main__':
    process()
