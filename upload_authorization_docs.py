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
from requests import get
from io import BytesIO
import pinyin

mongoClient = MongoClient(os.environ['VBA_DB_HOST'], int(os.environ['VBA_DB_PORT']))
# mongoClient = MongoClient('13.229.119.114', 27017)
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

    # open images
    logo = Image.open('epiapi_logo.png')
    box = Image.open('box.png')

    # get fonts
    font = ImageFont.truetype("fonts/Arial_Unicode.ttf", 28)
    boldFont = ImageFont.truetype("fonts/Arial_Unicode_Bold.ttf", 28)
    italicFont = ImageFont.truetype("fonts/Arial_Unicode_Italic.ttf", 26)
    heading = ImageFont.truetype("fonts/Arial_Unicode.ttf", 50)

    for doc in getPendingAuthorizationDocs(db.authorization_docs):
        try:
            img = Image.new('RGB', (1240,1754), (255,255,255))
            draw = ImageDraw.Draw(img)

            # heading
            draw.text((140, 80), 'EPIAPI - ID TRANSLATION', (0,0,0), font=heading)

            # logo
            img.paste(logo, (960, 40))

            # document info
            draw.text((140, 250), 'Prepared For', (0,0,0), font=boldFont)
            draw.text((380, 250), 'Synapse Financial Technologies Inc.', (0,0,0), font=font)
            draw.text((140, 300), 'Date', (0,0,0), font=boldFont)
            draw.text((380, 300), datetime.today().strftime('%d %B %Y'), (0,0,0), font=font)
            draw.text((140, 350), 'UserId', (0,0,0), font=boldFont)
            draw.text((380, 350), doc.get('userId'), (0,0,0), font=font)

            # box
            img.paste(box, (130, 425))
            # text with box
            draw.text((160, 450), 'Epiapi verifies the below information in relation to the userId provided above.', (0,0,0), font=italicFont)
            draw.text((160, 480), 'Epiapi staff review each ID manually prior to signing off on the below.', (0,0,0), font=italicFont)

            draw.text((140, 600), 'ORIGINAL', (0, 0, 0), font=ImageFont.truetype("fonts/Arial_Unicode_Bold.ttf", 40))
            idDocUri = doc.get('idDoc')

            curHeight = 700

            if idDocUri is not None and idDocUri != "":
                idDocResp = get(idDocUri)
                if idDocResp.status_code == 200:
                    basewidth = 580
                    with Image.open(BytesIO(idDocResp.content)) as idDocImg:
                        w, h = idDocImg.size

                        wpercent = (basewidth / float(w))
                        hsize = int((float(h) * float(wpercent)))
                        idDocImg = idDocImg.resize((basewidth, hsize), Image.ANTIALIAS)
                        img.paste(idDocImg, (140, 700))
                        curHeight += (hsize + 40)

            draw.text((140, curHeight), 'ENGLISH TRANSLATION', (0, 0, 0), font=ImageFont.truetype("fonts/Arial_Unicode_Bold.ttf", 40))

            draw.text((140, curHeight + 100), 'Fullname:', (0,0,0), font=boldFont)
            draw.text((420, curHeight + 100), doc.get('fullName'), (0,0,0), font=font)

            draw.text((140, curHeight + 140), 'Sex:', (0,0,0), font=boldFont)
            draw.text((420, curHeight + 140), doc.get('sex'), (0,0,0), font=font)

            draw.text((140, curHeight + 180), 'Ethnicity:', (0,0,0), font=boldFont)
            draw.text((420, curHeight + 180), doc.get('ethnicity'), (0,0,0), font=font)

            draw.text((140, curHeight + 220), 'Date of birth:', (0,0,0), font=boldFont)
            draw.text((420, curHeight + 220), doc.get('dobString'), (0,0,0), font=font)

            draw.text((140, curHeight + 260), 'Citizen ID Number:', (0,0,0), font=boldFont)
            draw.text((420, curHeight + 260), doc.get('citizenIdNumber'), (0,0,0), font=font)

            draw.text((140, curHeight + 300), 'Address:', (0,0,0), font=boldFont)
            street1 = doc.get('address').get('street1')
            street2 = doc.get('address').get('street2')
            city = doc.get('address').get('city')
            state = doc.get('address').get('state')
            postalCode = doc.get('address').get('postalCode')
            country = doc.get('address').get('country')
            address = "{} {} {} {}".format(city, state, postalCode, country)

            draw.text((420, curHeight + 300), street1, (0,0,0), font=font)
            paddingForStreet2 = 0
            if street2 != "":
                paddingForStreet2 = 40
                draw.text((420, curHeight + 340), street2, (0,0,0), font=font)
            draw.text((420, curHeight + 300 + paddingForStreet2 + 40), address, (0,0,0), font=font)

            # attach signature
            signatureImg = Image.open('{}.png'.format(doc.get('adminAccountId')))
            img.paste(signatureImg, (860, curHeight + 300 + paddingForStreet2 + 150))

            draw.text((900, curHeight + 300 + paddingForStreet2 + 120), 'Verified by:', (0,0,0), font=font)
            draw.text((900, curHeight + 300 + paddingForStreet2 + 270), doc.get('adminAccountName') if doc.get('adminAccountName') is not None else "", (0,0,0), font=font)

            userId = doc.get('userId')

            img.save('{}.pdf'.format(userId))

            with open('{}.pdf'.format(userId), mode='rb') as file: # b is important -> binary
                fileContent = file.read()
                user = User.by_id(client, userId, 'yes')
                for doc in user.base_documents:
                    if doc.email[-10:] != 'epiapi.com' and doc.email[-12:] != 'sendwyre.com':
                        doc.add_physical_document(type='AUTHORIZATION', mime_type='application/pdf', byte_stream=fileContent)

            os.remove('{}.pdf'.format(userId))

            # close signature
            signatureImg.close()

            # close img
            img.close()

            # mark to DONE after upload
            db.authorization_docs.update({'walletId':doc.get('walletId')}, {'$set':{'status':'DONE'}})
        except Exception as e:
            print(e)
            pass

    # close images
    logo.close()
    box.close()

if __name__ == '__main__':
    process()
