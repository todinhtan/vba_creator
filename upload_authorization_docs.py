from synapse_pay_rest.models.nodes import *
from synapse_pay_rest import User
from synapse_pay_rest import Client
from synapse_pay_rest import Node
from synapse_pay_rest import Subnet
import threading
import logging
import urllib
import json, os
from requests import get, post
from pymongo import MongoClient
from datetime import datetime
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

# mongoClient = MongoClient(os.environ['VBA_DB_HOST'], int(os.environ['VBA_DB_PORT']))
mongoClient = MongoClient('13.229.119.114', 27017)
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

#a. Create User
client = Client(**args)

def getPendingAuthorizationDocs(collection):
    pendingDocs = collection.find({'status': 'PENDING'})
    for doc in pendingDocs:
        yield doc

def process():
    threading.Timer(60, process).start()
    for doc in getPendingAuthorizationDocs(db.authorization_docs):
        try:
            font = ImageFont.truetype("Arial_Unicode.ttf", 14)
            img = Image.new('RGB', (595,842), (255,255,255))
            draw = ImageDraw.Draw(img)
            draw.text((100, 100), 'Fullname: {}'.format(doc.get('fullName')), (0,0,0), font=font)
            draw.text((100, 130), 'Sex: {}'.format(doc.get('sex')), (0,0,0), font=font)
            draw.text((100, 160), 'Ethnicity: {}'.format(doc.get('ethnicity')), (0,0,0), font=font)
            draw.text((100, 190), 'Date of birth: {}'.format(datetime.utcfromtimestamp(doc.get('dob') / 1000).strftime('%Y-%m-%d %H:%M:%S')), (0,0,0), font=font)
            draw.text((100, 220), 'Citizen ID Number: {}'.format(doc.get('citizenIdNumber')), (0,0,0), font=font)
            draw.text((100, 250), 'Address:', (0,0,0), font=font)
            draw.text((130, 280), 'Street1: {}'.format(doc.get('address').get('street1')), (0,0,0), font=font)
            draw.text((130, 310), 'Street2: {}'.format(doc.get('address').get('street2')), (0,0,0), font=font)
            draw.text((130, 340), 'City: {}'.format(doc.get('address').get('city')), (0,0,0), font=font)
            draw.text((130, 370), 'State: {}'.format(doc.get('address').get('state')), (0,0,0), font=font)
            draw.text((130, 400), 'Postal code: {}'.format(doc.get('address').get('postalCode')), (0,0,0), font=font)
            draw.text((130, 430), 'County: {}'.format(doc.get('address').get('country')), (0,0,0), font=font)

            # attach signature
            signatureImg = Image.open('{}.png'.format(doc.get('adminAccountId')))
            img.paste(signatureImg, (200, 600))

            userId = doc.get('userId')
            
            img.save('{}.pdf'.format(userId))

            with open('{}.pdf'.format(userId), mode='rb') as file: # b is important -> binary
                fileContent = file.read()
                user = User.by_id(client, userId)
                user.base_documents[0].add_physical_document(type='OTHER', mime_type='application/pdf', byte_stream=fileContent)

            os.remove('{}.pdf'.format(userId))
        except:
            pass


if __name__ == '__main__':
    process()