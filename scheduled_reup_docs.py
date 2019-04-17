from synapse_pay_rest.models.nodes import *
from synapse_pay_rest import User
from synapse_pay_rest import Client
from synapse_pay_rest import Node
from synapse_pay_rest import Subnet
import threading
import logging
import json, os
from requests import get, post
from pymongo import MongoClient
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
from io import BytesIO
from datetime import datetime
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

myip = get('https://api.ipify.org').text
args = {
    'client_id': os.environ['SYNAPSE_LIVE_ID'], # your client id
    'client_secret': os.environ['SYNAPSE_LIVE_SECRET'], # your client secret
    'fingerprint': '5af084654688ae0043d84603',
    'ip_address': myip, # user's IP
    'development_mode': False if os.environ['SYNAPSE_ENV'] == 'production' else True, # (optional) default False
    'logging': bool(os.environ['ON_DEBUG']) # (optional) default False # (optional) logs to stdout if True
}

client = Client(**args)

def getPendingScheduledDocs(collection):
    docs = collection.find({'status': 'PENDING'})
    for doc in docs:
        yield doc

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

def reupSynapseIdDoc(userId, idDoc, baseDocId, subDocId):
    user = User.by_id(client, userId, 'yes')
    data = getIdDoc(idDoc)
    if data is None:
        print("cannot upload: " + idDoc)
        return None
    
    document = None
    if baseDocId is not None and baseDocId != '':
        for doc in user.base_documents:
            if doc.id == baseDocId:
                document = doc
                break
    else:
        if len(user.base_documents) == 1:
            # if user has only one document, update it
            document = user.base_documents[0]
        elif len(user.base_documents) > 1:
            # if user has more than one document, update individual document (base on email)
            for doc in user.base_documents:
                if doc.email[-10:] != 'epiapi.com' and doc.email[-12:] != 'sendwyre.com':
                    document = doc
                    break

    if document is not None:
        # delete old doc if exist
        if subDocId is not None and subDocId != '':
            args = {
                'physical_documents': [{
                    'id': subDocId,
                    'document_type':'DELETE_DOCUMENT',
                    'document_value':'data:image/gif;base64,SUQs=='
                }]
            }
            document.update(**args)
        # add new
        document.add_physical_document(type='GOVT_ID_INT', mime_type='image/png', byte_stream=data)
    # get data of base docs as an array
    # iterate to find individual base doc if base_documents[i].email[-10:] != 'epiapi.com' and base_documents[i].email[-12:] != 'sendwyre.com'
    # idv_base_doc = base_documents[i]
    # use idv_base_doc for idv_base_doc.add_physical_document(type='GOVT_ID_INT', mime_type='image/png', byte_stream=data)

def reupSynapseCoiDoc(userId, coiDoc, baseDocId, subDocId):
    user = User.by_id(client, userId, 'yes')
    data = getIdDoc(coiDoc)
    if data is None:
        print("cannot upload: " + coiDoc)
        return None

    document = None
    if baseDocId is not None and baseDocId != '':
        for doc in user.base_documents:
            if doc.id == baseDocId:
                document = doc
                break
    else:
        if len(user.base_documents) == 1:
            # if user has only one document, update it
            document = user.base_documents[0]
        elif len(user.base_documents) > 1:
            # if user has more than one document, update company document (base on email)
            for doc in user.base_documents:
                if doc.email[-10:] == 'epiapi.com' or doc.email[-12:] == 'sendwyre.com':
                    document = doc
                    break

    if document is not None:
        # delete old doc if exist
        if subDocId is not None and subDocId != '':
            args = {
                'physical_documents': [{
                    'id': subDocId,
                    'document_type':'DELETE_DOCUMENT',
                    'document_value':'data:image/gif;base64,SUQs=='
                }]
            }
            document.update(**args)
        # add new
        document.add_physical_document(type='OTHER', mime_type='image/png', byte_stream=data)
    # get data of base docs as an array
    # iterate to find company base doc if base_documents[i].email[-10:] == 'epiapi.com' or base_documents[i].email[-12:] == 'sendwyre.com'
    # comp_base_doc = base_documents[i]
    # use comp_base_doc for comp_base_doc.add_physical_document(type='OTHER', mime_type='image/png', byte_stream=data)

def uploadAuthorizedDoc(userId, doc, baseDocId, subDocId):
    # open images
    logo = Image.open('epiapi_logo.png')
    box = Image.open('box.png')

    # get fonts
    font = ImageFont.truetype("fonts/Arial_Unicode.ttf", 28)
    boldFont = ImageFont.truetype("fonts/Arial_Unicode_Bold.ttf", 28)
    italicFont = ImageFont.truetype("fonts/Arial_Unicode_Italic.ttf", 26)
    heading = ImageFont.truetype("fonts/Arial_Unicode.ttf", 50)

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
    draw.text((380, 350), userId, (0,0,0), font=font)

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

    img.save('{}.pdf'.format(userId))

    with open('{}.pdf'.format(userId), mode='rb') as file: # b is important -> binary
        fileContent = file.read()
        user = User.by_id(client, userId, 'yes')

        document = None
        if baseDocId is not None and baseDocId != '':
            for doc in user.base_documents:
                if doc.id == baseDocId:
                    document = doc
                    break
        else:
            if len(user.base_documents) == 1:
                # if user has only one document, update it
                document = user.base_documents[0]
            elif len(user.base_documents) > 1:
                # if user has more than one document, update individual document (base on email)
                for doc in user.base_documents:
                    if doc.email[-10:] != 'epiapi.com' and doc.email[-12:] != 'sendwyre.com':
                        document = doc
                        break

        if document is not None:
            # delete old doc if exist
            if subDocId is not None and subDocId != '':
                args = {
                    'physical_documents': [{
                        'id': subDocId,
                        'document_type':'DELETE_DOCUMENT',
                        'document_value':'data:image/gif;base64,SUQs=='
                    }]
                }
                document.update(**args)
            # add new
            document.add_physical_document(type='AUTHORIZATION', mime_type='application/pdf', byte_stream=fileContent)

    os.remove('{}.pdf'.format(userId))

    # close signature
    signatureImg.close()

    # close img
    img.close()

    # close images
    logo.close()
    box.close()

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

def reupAMZCapturedImg(userId, amz_id, baseDocId, subDocId):
    user = User.by_id(client, userId, 'yes')
    data = getAMZImg(amz_id)
    if data is None:
        print("cannot upload: " + amz_id)
        return None

    document = None
    if baseDocId is not None and baseDocId != '':
        for doc in user.base_documents:
            if doc.id == baseDocId:
                document = doc
                break
    else:
        if len(user.base_documents) == 1:
            # if user has only one document, update it
            document = user.base_documents[0]
        elif len(user.base_documents) > 1:
            # if user has more than one document, update company document (base on email)
            for doc in user.base_documents:
                if doc.email[-10:] == 'epiapi.com' or doc.email[-12:] == 'sendwyre.com':
                    document = doc
                    break

    if document is not None:
        # delete old doc if exist
        if subDocId is not None and subDocId != '':
            args = {
                'physical_documents': [{
                    'id': subDocId,
                    'document_type':'DELETE_DOCUMENT',
                    'document_value':'data:image/gif;base64,SUQs=='
                }]
            }
            document.update(**args)
        # add new
        document.add_physical_document(type='OTHER', mime_type='image/png', byte_stream=data)

    # find company base doc same as function reupSynapseCoiDoc

def markDoneScheduledDoc(_id):
    db.scheduled_reup_docs.update({'_id':_id}, {'$set':{'status':'DONE'}})

def getVbaByWalletId(walletId):
    vba = db.vbarequests.find_one({'country': 'US', 'walletId': walletId})
    return vba

def process():
    threading.Timer(2 * 60, process).start()

    for pendingDoc in getPendingScheduledDocs(db.scheduled_reup_docs):
        docType = pendingDoc.get('docType')
        _id = pendingDoc.get('_id')
        baseDocId = pendingDoc.get('baseDocId')
        subDocId = pendingDoc.get('subDocId')

        # skip if docType not found!
        if docType is None:
            continue

        # proceed based on docType
        walletId = pendingDoc.get('walletId')
        userId = pendingDoc.get('userId')
        if docType == 'authorization':
            authorizedData = pendingDoc.get('authorizationData')
            uploadAuthorizedDoc(userId, authorizedData, baseDocId, subDocId)
        elif docType == 'idDoc':
            vba = getVbaByWalletId(walletId)
            if vba is not None:
                idDoc = vba.get('idDoc')
                if idDoc is not None:
                    reupSynapseIdDoc(userId, idDoc, baseDocId, subDocId)
        elif docType == 'coiDoc':
            vba = getVbaByWalletId(walletId)
            if vba is not None:
                coiDoc = vba.get('coiDoc')
                if coiDoc is not None:
                    reupSynapseCoiDoc(userId, coiDoc, baseDocId, subDocId)
        elif docType == 'amz':
            vba = getVbaByWalletId(walletId)
            merchantIds = vba.get('merchantIds')
            print(merchantIds)
            if merchantIds is not None and len(merchantIds) > 0:
                merchantId = merchantIds[0].get('merchantId')
                if merchantId is not None:
                    reupAMZCapturedImg(userId, merchantId, baseDocId, subDocId)
        elif docType == 'basic' or docType == 'company_basic': # individual basic
            user = User.by_id(client, userId, 'yes')
            print(user)
            userData = pendingDoc.get('userData')
            print(baseDocId)
            if baseDocId is not None and baseDocId != '':
                payload = {
                    'documents': [{
                        'id': baseDocId,
                        'email': userData.get('email'),
                        'phone_number': userData.get('phone_number'),
                        'ip': userData.get('ip'),
                        'address_street': userData.get('address_street'),
                        'address_city': userData.get('address_city'),
                        'address_subdivision': userData.get('address_subdivision'),
                        'address_postal_code': userData.get('address_postal_code'),
                        'address_country_code': userData.get('address_country_code'),
                        'day': userData.get('day'),
                        'month': userData.get('month'),
                        'year': userData.get('year'),
                    }]
                }
                client.users.update(userId, payload)

        # mark record status = DONE after processing
        markDoneScheduledDoc(_id)

if __name__ == '__main__':
    process()
