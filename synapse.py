import io, os, traceback
import hashlib
import urllib
import json
import time
from requests import get,post
from synapse_pay_rest.models.nodes import *
from synapse_pay_rest import User
from synapse_pay_rest import Client
from synapse_pay_rest import Node
from synapse_pay_rest import Subnet
import logging
from lib.epiapi import epiapi
import pinyin
from pymongo import MongoClient
import threading
import graypy
import shutil


# file_path = 'NECONSENT.pdf'

grayLogger = logging.getLogger('graylog')
grayLogger.setLevel(logging.CRITICAL)
handler = graypy.GELFHandler(os.environ['GRAYLOG_HOST'], int(os.environ['GRAYLOG_PORT']))
grayLogger.addHandler(handler)

logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = logging.Formatter(
    '%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)


def verifyEpiApiInputs(body):
    walletId = body.get('walletId', None)
    wyreCredentials = body.get('wyreCredentials', None)
    if walletId is None:
        return {'error':'walletId is required'}
    if wyreCredentials is None:
        return {'error':'wyreCredentials is required'}
    if wyreCredentials.get('accountId') is None or wyreCredentials.get('apiKey') is None or wyreCredentials.get('apiSecKey') is None:
        return {'error':'wyreCredentials is invalid\nwyreCredentials format should be:{}'.format(json.dumps({'accountId':'string','apiKey':'string','apiKey':'string'}))}
    return None, walletId, wyreCredentials

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

def getWallet(walletId):
    http_code, walletInfo = epiapiCli.get_wallet(walletId)
    if http_code >= 400:
        return {'error':walletInfo}
    return None, walletInfo

def verifyWalletVBA(walletId, vbaVerification):
    if vbaVerification is None:
        return {'error': 'VBA is empty'}
    # requiredFields = ['email', 'phoneNumber', 'entityType', 'entityScope', 'dateOfBirth', 'shopName', 'address']
    defaultFields = {'email':walletId+'@epiapi.com', 'phoneNumber':'required', 'entityType':'NOT_KNOWN', 'entityScope':'Not Known', 'dateOfBirth':'required', 'shopName':'not know', 'address':'required'}
    defaultAddress = {'street1':'1', 'street2':'somewhere', 'city':'Henan', 'state':'HE', 'postalCode':'1000027', 'country':'CN'}
    defaultNames = {'nameEn':'Unknow', 'nameCn':'Unknow'}

    for key, value in defaultFields.items():
        if vbaVerification.get(key,None) is None:
            if defaultFields.get(key) == 'required':
                return {'error':'vbaVerification miss {}'.format(key)}, None
            vbaVerification[key] = defaultFields.get(key)
    address = vbaVerification.get("address")
    for key, value in defaultAddress.items():
        if address.get(key,None) is None:
            if defaultAddress.get(key) == 'required':
                return {'error':'vbaVerification miss {}'.format(key)}, None
            vbaVerification[key] = defaultAddress.get(key)

    vbaVerification['isBusiness'] = vbaVerification.get('entityType') == 'CORP'

    return None, vbaVerification

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

def createSynapseUser(srn, data):
    try:
        name = pinyin.get(data.get("nameCn"), format="strip", delimiter=" ") if (data.get('nameCn', None) != '' and data.get('nameCn', None) != None) else data.get("nameEn")
        args = {
            'email': data.get('email'),
            'phone_number': data.get('phoneNumber'),
            'legal_name': name,
            'supp_id': srn,
            'is_business': data.get('isBusiness'), # default False first
            'cip_tag': 1
        }
        return None, User.create(client, **args)
    except Exception as e:
        logger.debug(traceback.format_exc())
        return {'error': str(e)}, None

def addBasisDocument(user, data):
    try:
        address = data.get('address')
        addressstreetstrings = [address.get("street1"),address.get("street2")]
        addressstreetstrings = ' '.join(filter(None, addressstreetstrings))
        address_street = pinyin.get(addressstreetstrings, format="strip", delimiter=" ")
        address_street = address_street if len(address_street.split()) == len(addressstreetstrings) else addressstreetstrings

        address_subdivision = pinyin.get(address.get('state'), format="strip", delimiter=" ")
        address_subdivision = address_subdivision if len(address_subdivision.split()) == len(address.get('state')) else address.get('state')

        address_city = pinyin.get(address.get('city'), format="strip", delimiter=" ")
        address_city = address_city if len(address_city.split()) == len(address.get('city')) else address.get('city')

        dateOfBirth = data.get("dateOfBirth")
        day = time.strftime("%d", time.localtime(int(dateOfBirth/1000)))
        month = time.strftime("%m", time.localtime(int(dateOfBirth/1000)))
        year = time.strftime("%Y", time.localtime(int(dateOfBirth/1000)))
        #print("nameCn", data.get('nameCn'))
        if data.get('isBusiness') == True:
            name = pinyin.get(data.get("companyNameCn"), format="strip", delimiter=" ") if (data.get('companyNameCn', None) != '' and data.get('companyNameCn', None) != None) else data.get("companyNameEn")
        else:
            name = pinyin.get(data.get("nameCn"), format="strip", delimiter=" ") if (data.get('nameCn', None) != '' and data.get('nameCn', None) != None) else data.get("nameEn")
        options = {
            'email': data.get('email'),
            'phone_number': data.get('phoneNumber'),
            'ip': myip,
            'name': name,
            'alias': data.get('shopName'),
            'entity_type': data.get('entityType'),
            'entity_scope': data.get('entityScope'),
            'day': int(day),
            'month': int(month),
            'year': int(year),
            'address_street': address_street,
            'address_city': address_city,
            'address_subdivision': address_subdivision,
            # 'address_subdivision': 'HA',
            'address_postal_code': address.get('postalCode'),
            # 'address_country_code': address_country_code
            'address_country_code': address.get('country')
        }
        #print("add document options:")
        #print(options)
        res = user.add_base_document(**options)
        return None, res
    except Exception as e:
        logger.debug(traceback.format_exc())
        return {'error': str(e)}, None

def addBusinessDocument(user, base_document, data, walletId):
    try:
        if data.get('isBusiness') == True:
            time.sleep(3)
        else:
            return None
        co_regid = data.get('registrationNumber')
        phone_number = data.get('phoneNumber')
        alias = data.get('shopName')
        legal_name_ind = pinyin.get(data.get("companyNameCn"), format="strip", delimiter=" ") if (data.get('companyNameCn', None) != '' and data.get('companyNameCn', None) != None) else data.get("companyNameEn")
        address = data.get('address')
        addressstreetstrings = [address.get("street1"),address.get("street2")]
        addressstreetstrings = ' '.join(filter(None, addressstreetstrings))
        address_street = pinyin.get(addressstreetstrings, format="strip", delimiter=" ")
        address_street = address_street if len(address_street) == len(addressstreetstrings) else addressstreetstrings

        address_subdivision = pinyin.get(address.get('state'), format="strip", delimiter=" ")
        address_subdivision = address_subdivision if len(address_subdivision) == len(address.get('state')) else address.get('state')

        address_city = pinyin.get(address.get('city'), format="strip", delimiter=" ")
        address_city = address_city if len(address_city) == len(address.get('city')) else address.get('city')

        dateOfBirth = data.get("dateOfBirth")
        day = time.strftime("%d", time.localtime(int(dateOfBirth/1000)))
        month = time.strftime("%m", time.localtime(int(dateOfBirth/1000)))
        year = time.strftime("%Y", time.localtime(int(dateOfBirth/1000)))

        virtual_document = base_document.add_virtual_document(type='OTHER', value=co_regid)
        base_document = virtual_document.base_document

        http_code, docImageInfo = epiapiCli.get_coi(data.get('idDoc'))
        real_img_resp = get(docImageInfo['uri'])
        if real_img_resp.status_code != 200:
            return {'error': 'cannot download doc:' + data.get('idDoc')}
        docImage = real_img_resp.content
        base_document.add_physical_document(type='OTHER', mime_type='image/png', byte_stream=docImage)
        kwargs = {
            'email': walletId+'@sendwyre.com',
            'phone_number': '0086'+phone_number,
            'name': legal_name_ind,
            'ip': myip,
            'alias': alias,
            'entity_type': data.get('entityType'),
            'entity_scope': data.get('entityScope'),
            'day': int(day),
            'month': int(month),
            'year': int(year),
            'address_street': address_street,
            'address_city': address_city,
            'address_subdivision': address_subdivision,
            # 'address_subdivision': 'HA',
            'address_postal_code': address.get('postalCode'),
            # 'address_country_code': address_country_code
            'address_country_code': address.get('country')
        }
        base_document2 = user.add_base_document(**kwargs)
        http_code, docImageInfo = epiapiCli.get_govid(data.get('idDoc'))
        real_img_resp = get(docImageInfo['uri'])
        if real_img_resp.status_code != 200:
            return {'error': 'cannot download doc:' + data.get('idDoc')}
        docImage = real_img_resp.content
        base_document2.add_physical_document(type='GOVT_ID_INT', mime_type='image/png', byte_stream=docImage)
        return None
    except Exception as e:
        logger.debug(traceback.format_exc())
        return {'error': str(e)}

def get_shop_img(amz_id):
    # will get stuck when using phantomjs
    amzurl = 'https://www.amazon.com/s?merchant='+amz_id
    resp = post('http://{}:8081'.format(os.environ.get('WEB_CAPTURE_URL','localhost')), data={'url':amzurl}, headers={'Content-Type':'Application/Json'})
    print('get_shop_img:'+str(resp.status_code))
    if resp.status_code == 200:
        return resp.content
    return None

def getConsent(accountSRN):
    print(accountSRN)
    accountId = accountSRN.split(":")[1]
    file_path = {
        "AC-LT8PTPBLEDA": "NECONSENT",
        "AC-LRZYD3PTQF7": "BFCONSENT",
        "AC-CBH3TFZRT3D": "DDCONSENT"
    }.get(accountId,"NECONSENT") + ".pdf"
    physical_document_name = accountId + ".pdf"
    shutil.copyfile(file_path, physical_document_name)
    return physical_document_name

def addPhysicalDocument(base_document, data, accountId):
    try:
        physical_document_name = getConsent(accountId)
        base_document.add_physical_document(type='OTHER', file_path=physical_document_name) # Consent
        os.remove(physical_document_name)
        shop_file_path = 'amz_mainpage.png'
        shop_file_bytes = None
        if len(data['merchantIds']) > 0:
            shop_file_bytes = get_shop_img(data['merchantIds'][0]['merchantId'])
        if shop_file_bytes is not None:
            base_document.add_physical_document(type='OTHER', mime_type='image/png', byte_stream=shop_file_bytes) # Shop Screengrab
        else:
            base_document.add_physical_document(type='OTHER', mime_type='image/png', file_path=shop_file_path) # Shop Screengrab
        value = 'data:image/png;base64,SUQs=='
        base_document.add_physical_document(type='OTHER', value=value) # Blank Doc

        http_code, docImageInfo = epiapiCli.get_govid(data.get('idDoc'))
        real_img_resp = get(docImageInfo['uri'])
        if real_img_resp.status_code != 200:
            return {'error': 'cannot download doc:' + data.get('idDoc')}
        docImage = real_img_resp.content
        physical_document = base_document.add_physical_document(type='GOVT_ID_INT', mime_type='image/png', byte_stream=docImage) # Government ID
        return None, physical_document.base_document
    except Exception as e:
        logger.debug(traceback.format_exc())
        return {'error': str(e)}, None

def createNode(srn, user):
    try:

        accountId = srn.split(":")[1]
        nickname = {
                    "AC-LT8PTPBLEDA": "account:AC-B6TLMTQUEMC",
                    "AC-LRZYD3PTQF7": "account:AC-FJW38ZBQJ9Y",
                    "AC-CBH3TFZRT3D": "account:AC-L6TZ4R9EEBZ"
        }.get(accountId,srn)
        required = {
            'nickname': nickname
        }
        return None, SubaccountUsNode.create(user, **required)
    except Exception as e:
        logger.debug(traceback.format_exc())
        return {'error': str(e)}, None

def createSubnet(srn, node):
    try:
        args = {
            'nickname': srn
        }
        return None, Subnet.create(node, **args)
    except Exception as e:
        logger.debug(traceback.format_exc())
        return {'error': str(e)}, None

def updateWallet(walletId, vbaData):
    http_code, info = epiapiCli.update_wallet(walletId, vbaData)
    if http_code >= 400:
        return {'error':info}
    return None

def getSynapseData(userId,nodeId,subnetId):
    user = User.by_id(client, userId)
    node = Node.by_id(user, nodeId)
    subnet = Subnet.by_id(node, subnetId)
    return user, node, subnet

def fromSynapseResponse(synapseUser, synapseNode, synapseSubnet):
    myuserjson = getattr(synapseUser, 'json')
    mynodejson = getattr(synapseNode, 'json')
    mysubnetjson = getattr(synapseSubnet, 'json')

    vbaData = {
        "bankAddress": "6070 Poplar Ave #100, Memphis TN 38119",
        "bankName": "Evolve Bank & Trust",
        "accountNumber": getattr(synapseSubnet, 'account_num'),
        "routingNumber": getattr(synapseSubnet, 'routing_num_ach'),
        "beneficiaryName": getattr(synapseUser, 'legal_names')[0]
    }

    #print("synapseUser")
    #print(synapseUser)
    #print("synapseNode")
    #print(synapseNode)
    #print("synapseSubnet")
    #print(synapseSubnet)
    ids = {'userId':myuserjson.get("_id"), 'nodeId':mynodejson.get("_id"), 'subnetId':mysubnetjson.get("_id"), 'accountNum':mysubnetjson.get("account_num")}
    permission = myuserjson.get("permission")
    doc_status = myuserjson.get("doc_status")
    vbaData['status_doc'] = doc_status
    vbaData['status'] = permission
    vbaData.update(ids)
    status = "WAITING_FOR_APPROVAL" if vbaData["accountNumber"] is None or permission == 'UNVERIFIED' else "APPROVED"
    return vbaData, status

def getPendingRequest():
    vbaRequests = db.vbarequests.find({"walletType":"VBA","country":"US", "status":"PENDING", "idDoc": {"$exists":True, "$ne":None}})
    for req in vbaRequests:
        yield req

def getWaitForApprovalRequest():
    vbaRequests = db.vbarequests.find({"country":"US", "status":"WAITING_FOR_APPROVAL"})
    for req in vbaRequests:
        yield req

mongoClient = MongoClient(os.environ['VBA_DB_HOST'], int(os.environ['VBA_DB_PORT']))
db = mongoClient.vba_service

def updateVBA(req, status):
    db.vbarequests.update({'_id':req.get('_id')}, {'$set':{'vbaData':req.get('vbaData'), 'status':status}})

def updateVBAFail(req):
    db.vbarequests.update({'_id':req.get('_id')}, {'$set': {'status':'DENIED'}})

def createVBA(vbaRequest):
    walletId = vbaRequest.get('walletId')
    accountId = vbaRequest.get('accountId')
    # verify wallet's vbaVerificationData is valid
    error, synapseUserData = verifyWalletVBA(walletId, vbaRequest)
    if error is not None:
        logger.error(error)
        grayLogger.critical(error['error'], extra={'type': 'verifyWalletVBA', 'vbaRequest':vbaRequest})
        updateVBAFail(vbaRequest)
        return
    # create new synapse user for the wallet
    error, synapseUser = createSynapseUser("wallet:"+walletId, vbaRequest)
    if error is not None:
        logger.error(error)
        grayLogger.critical(error['error'], extra={'type': 'createSynapseUser', 'vbaRequest':vbaRequest})
        updateVBAFail(vbaRequest)
        return
    # add basis document which are basis contact information
    error, baseDocument = addBasisDocument(synapseUser, vbaRequest)
    if error is not None:
        logger.error(error)
        grayLogger.critical(error['error'], extra={'type': 'addBasisDocument', 'vbaRequest':vbaRequest})
        updateVBAFail(vbaRequest)
        return

    error = addBusinessDocument(synapseUser, baseDocument, vbaRequest, walletId)
    if error is not None:
        logger.error(error)
        grayLogger.critical(error['error'], extra={'type': 'addBusinessDocument', 'vbaRequest':vbaRequest})
        updateVBAFail(vbaRequest)
        return

    error, baseDocument = addPhysicalDocument(baseDocument, vbaRequest, accountId)
    if error is not None:
        logger.error(error)
        grayLogger.critical(error['error'], extra={'type': 'addPhysicalDocument', 'vbaRequest':vbaRequest})
        updateVBAFail(vbaRequest)
        return

    error, synapseNode = createNode(accountId, synapseUser)
    if error is not None:
        logger.error(error)
        grayLogger.critical(error['error'], extra={'type': 'createNode', 'synapseUser':vbaRequest})
        updateVBAFail(vbaRequest)
        return

    error, synapseSubnet = createSubnet("wallet:"+walletId, synapseNode)
    if error is not None:
        logger.error(error)
        grayLogger.critical(error['error'], extra={'type': 'createSubnet', 'synapseNode':vbaRequest})
        updateVBAFail(vbaRequest)
        return

    vbaRequest['vbaData'], status = fromSynapseResponse(synapseUser, synapseNode, synapseSubnet)
    updateVBA(vbaRequest,'WAITING_FOR_APPROVAL')

def checkAndUpdateVBA(vbaRequest):
    userId = vbaRequest.get('vbaData').get('userId')
    nodeId = vbaRequest.get('vbaData').get('nodeId')
    subnetId = vbaRequest.get('vbaData').get('subnetId')
    synapseUser,synapseNode,synapseSubnet = getSynapseData(userId,nodeId,subnetId)
    vbaRequest['vbaData'], status = fromSynapseResponse(synapseUser, synapseNode, synapseSubnet)
    updateVBA(vbaRequest, status)


def process():
    threading.Timer(5 * 60, process).start()
    for vbaRequest in getPendingRequest():
        createVBA(vbaRequest)
    for vbaRequest in getWaitForApprovalRequest():
        checkAndUpdateVBA(vbaRequest)

if __name__ == '__main__':
    process()
