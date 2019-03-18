from synapse_pay_rest.models.nodes import *
from synapse_pay_rest import User
from synapse_pay_rest import Client
from synapse_pay_rest import Node
from synapse_pay_rest import Subnet
import logging
from lib.epiapi import epiapi
import urllib
import json, os
from requests import get
from pymongo import MongoClient

mongoClient = MongoClient(os.environ['VBA_DB_HOST'], int(os.environ['VBA_DB_PORT']))
db = mongoClient.vba_service

def createEpiApi(credentials):
    account_id = credentials.get('accountId', None)
    api_key = credentials.get('apiKey', None)
    secret_key = credentials.get('apiSecKey', None)
    return epiapi(account_id, 'v2', api_key, secret_key)


    # "owner": "account:AC-XFVPWXR33XC",
    # "createdAt": 1552444336048,
    # "expiresAt": null,
    # "apiKey": "AK-F9UQ2X4G-RAL9JAJ7-DMYCAAMM-ZM3BVLMT",
    # "desc": "",
    # "ipWhitelist": [],
    # "destSrnWhitelist": [],
    # "secretKey": "SK-NA4H3GDQ-GZG7Y9VU-D4GY7P96-97PQLUNF"

    # epiapiCli = createEpiApi({
    #     "accountId": "account:AC-6TBVQL9WHWQ",
    #     "apiKey": "AK-JNZFUC3D-N4R3NPFP-Y8L6F6ER-ZBFG2PMW",
    #     "apiSecKey": "SK-CLFUJHHW-G7F4Y4DZ-WDTHNJP6-EGBRDLF4"
    # })

epiapiCli = createEpiApi({
    "accountId": os.environ['EPIAPI_ADMIN_ACCOUNTID'],
    "apiKey": os.environ['EPIAPI_ADMIN_APIKEY'],
    "apiSecKey": os.environ['EPIAPI_ADMIN_SECRET']
})
myip = get('https://api.ipify.org').text
args = {
    'client_id': os.environ['SYNAPSE_LIVE_ID'], # your client id
    'client_secret': os.environ['SYNAPSE_LIVE_SECRET'], # your client secret
    'fingerprint': '5af084654688ae0043d84603',
    'ip_address': myip, # user's IP
    'development_mode': False if os.environ['SYNAPSE_ENV'] == 'production' else True, # (optional) default False
    'logging': bool(os.environ['ON_DEBUG']) # (optional) default False # (optional) logs to stdout if True
}
#print("synapse environment:\n")
#print(args)

#a. Create User
client = Client(**args)

def getIdDoc(idDoc):
    if 'http' in idDoc:
        uri = idDoc
    else:
        status, data = epiapiCli.get_govid(idDoc)
        uri = data['uri']
    resp = get(uri)
    if resp.status_code != 200:
        return None
    return resp.content

def getCoiDoc(coiDoc):
    if 'http' in coiDoc:
        uri = coiDoc
    else:
        status, data = epiapiCli.get_govid(coiDoc)
        uri = data['uri']
    resp = get(uri)
    if resp.status_code != 200:
        return None
    return resp.content


def reupSynapseIdDoc(userId, idDoc):
    user = User.by_id(client, userId)
    data = getIdDoc(idDoc)
    if data is None:
        print("cannot upload: " + idDoc)
        return None
    user.base_documents[0].add_physical_document(type='GOVT_ID_INT', mime_type='image/png', byte_stream=data)

def reupSynapseCoiDoc(userId, coiDoc):
    user = User.by_id(client, userId)
    data = getIdDoc(coiDoc)
    if data is None:
        print("cannot upload: " + coiDoc)
        return None
    user.base_documents[0].add_physical_document(type='OTHER', mime_type='image/png', byte_stream=data)

def getSubmittedAndValidDocRequests(collection):
    vbaRequests = collection.find({'country': 'US', 'status': 'APPROVED', 'vbaData.status_doc.physical_doc': 'SUBMITTED|VALID'})
    for req in vbaRequests:
        yield req

def findAndReupSynapseDoc():
    for req in getSubmittedAndValidDocRequests(db.vbarequests):
        try:
            vbaData = req.get('vbaData')
            userId = vbaData.get('userId')
            if userId is not None:
                idDoc = req.get('idDoc')
                coiDoc = req.get('coiDoc')
                if idDoc is not None:
                    reupSynapseIdDoc(userId, idDoc)
                if coiDoc is not None:
                    reupSynapseCoiDoc(userId, coiDoc)
        except:
            pass

if __name__ == '__main__':
    findAndReupSynapseDoc()
# reupSynapseDoc('5c88784a5ac648006671721a',data)

#TODO:
# 1. Find vbarequests where : {country:"US", status:"APPROVED", "vbaData.status_doc.physical_doc" : "SUBMITTED|VALID" }
# 2. loop thru and call reupSynapseIdDoc if idDoc exists and not null
# 3. loop thru and call reupSynapseCoiDoc if coiDoc exists and not null
# note that vbaData.userId as param userId in reupSynapseIdDoc and reupSynapseCoiDoc
