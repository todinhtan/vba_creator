from synapse_pay_rest.models.nodes import *
from synapse_pay_rest import User
from synapse_pay_rest import Client
from synapse_pay_rest import Node
from synapse_pay_rest import Subnet
import logging
from lib.epiapi import epiapi
import urllib
import json, os
from requests import get, post
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
    'logging': bool(os.environ['ON_DEBUG']) # (optional) default False # (optional) logs to stdout if True
}
#print("synapse environment:\n")
#print(args)

#a. Create User
client = Client(**args)

def getAMZImg(amz_id):
    # will get stuck when using phantomjs
    amzurl = 'https://www.amazon.com/s?merchant='+amz_id
    capture_url = 'http://{}:8081'.format(os.environ.get('WEB_CAPTURE_URL','localhost'))
    print(capture_url)
    print({ 'url':amzurl })
    resp = post(capture_url, data=json.dumps({ "url":amzurl }), headers={'Content-Type':'application/json'})
    print('get_shop_img:'+str(resp.status_code))
    if resp.status_code == 200:
        return resp.content
    return None

def reupAMZCapturedImg(userId, amz_id):
    user = User.by_id(client, userId)
    data = getAMZImg(amz_id)
    if data is None:
        print("cannot upload: " + amz_id)
        return None
    user.base_documents[0].add_physical_document(type='OTHER', mime_type='image/png', byte_stream=data)

def getSubmittedAndValidDocRequests(collection):
    vbaRequests = collection.find({'country': 'US', 'status': 'APPROVED', 'vbaData.status_doc.physical_doc': 'SUBMITTED|VALID'})
    for req in vbaRequests:
        yield req

def findAndReup():
    for req in getSubmittedAndValidDocRequests(db.vbarequests):
        try:
            vbaData = req.get('vbaData')
            userId = vbaData.get('userId')
            print(userId)
            if userId is not None:
                merchantIds = req.get('merchantIds')
                if merchantIds is not None and len(merchantIds) > 0:
                    merchantId = merchantIds[0].get('merchantId')
                    if merchantId is not None:
                        reupAMZCapturedImg(userId,merchantId)
        except:
            pass

if __name__ == '__main__':
    findAndReup()
# reupSynapseDoc('5c88784a5ac648006671721a',data)

#TODO:
# 1. Find vbarequests where : {country:"US", status:"APPROVED", "vbaData.status_doc.physical_doc" : "SUBMITTED|VALID" }
# 2. loop thru and call reupSynapseIdDoc if idDoc exists and not null
# 3. loop thru and call reupSynapseCoiDoc if coiDoc exists and not null
# note that vbaData.userId as param userId in reupSynapseIdDoc and reupSynapseCoiDoc
