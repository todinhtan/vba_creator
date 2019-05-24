import argparse
import sys
import json, os, traceback
from pymongo import MongoClient
from synapse_pay_rest.models.nodes import *
from synapse_pay_rest import User
from synapse_pay_rest import Client
from synapse_pay_rest import Node
from synapse_pay_rest import Subnet
from requests import get
import time
import pinyin

mongoClient = MongoClient(os.environ['VBA_DB_HOST'], int(os.environ['VBA_DB_PORT']))
db = mongoClient.vba_service

parser = argparse.ArgumentParser(description='fix missing base doc')

parser.add_argument('--wallets', action="store", dest='wallets', default=None)
parser.add_argument('--missing_doc', action="store", dest='missing_doc', default=None)

args = parser.parse_args()

myip = get('https://api.ipify.org').text

synapseArgs = {
    'client_id': os.environ['SYNAPSE_LIVE_ID'], # your client id
    'client_secret': os.environ['SYNAPSE_LIVE_SECRET'], # your client secret
    'fingerprint': '5af084654688ae0043d84603',
    'ip_address': myip, # user's IP
    'development_mode': False if os.environ['SYNAPSE_ENV'] == 'production' else True, # (optional) default False
    'logging': bool(os.environ['ON_DEBUG']) # (optional) default False # (optional) logs to stdout if True
}

client = Client(**synapseArgs)

def getVbaRequestByWalletId(walletId):
    vbaRequest = db.vbarequests.find_one({ 'walletId': walletId, 'country': 'US' })
    return vbaRequest

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
        day = time.strftime("%d", time.localtime(int(float(dateOfBirth)/1000)))
        month = time.strftime("%m", time.localtime(int(float(dateOfBirth)/1000)))
        year = time.strftime("%Y", time.localtime(int(float(dateOfBirth)/1000)))
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
        res = user.add_base_document(**options)
        return None, res
    except Exception as e:
        print(traceback.format_exc())
        return {'error': str(e)}, None

def addBusinessDocument(user, data, walletId):
    try:
        phone_number = data.get('phoneNumber')
        alias = data.get('shopName')
        legal_name_ind = pinyin.get(data.get("companyNameCn"), format="strip", delimiter=" ") if (data.get('companyNameCn', None) != '' and data.get('companyNameCn', None) != None) else data.get("companyNameEn")


        address = data.get('address')
        addressstreetstrings = [address.get("street1"),address.get("street2")]
        addressstreetstrings = ' '.join(filter(None, addressstreetstrings))
        address_street = pinyin.get(addressstreetstrings, format="strip", delimiter=" ")
        address_street = address_street if len(address_street.split()) == len(addressstreetstrings) else addressstreetstrings

        address_subdivision = pinyin.get(address.get('state'), format="strip", delimiter=" ")
        address_subdivision = address_subdivision if len(address_subdivision.split()) == len(address.get('state')) else address.get('state')

        address_city = pinyin.get(address.get('city'), format="strip", delimiter=" ")
        address_city = address_city if len(address_city.split()) == len(address.get('city')) else address.get('city')

        dateOfEstablishment = data.get("dateOfEstablishment")
        day = time.strftime("%d", time.localtime(int(float(dateOfEstablishment)/1000)))
        month = time.strftime("%m", time.localtime(int(float(dateOfEstablishment)/1000)))
        year = time.strftime("%Y", time.localtime(int(float(dateOfEstablishment)/1000)))

        kwargs = {
            'email': walletId+'@epiapi.com',
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
        res = user.add_base_document(**kwargs)
        return None, res
    except Exception as e:
        traceback.print_exc()
        return {'error': str(e)}, None

def process():
    walletsArg = args.wallets
    missingDoc = args.missing_doc

    if walletsArg is None or missingDoc is None:
        print('Both wallets and missing_doc parameters are required.')
        sys.exit()

    if missingDoc not in ['individual', 'company']:
        print('missing_doc must only be individual or company')
        sys.exit()

    walletIds = walletsArg.split(',')
    for walletId in walletIds:
        if walletId != '':
            vbaRequest = getVbaRequestByWalletId(walletId)
            vbaData = vbaRequest.get('vbaData')

            if vbaData is None:
                print('There is no userId for wallet {}'.format(walletId))
                continue
            
            userId = vbaData.get('userId')
            if userId is None:
                print('There is no userId for wallet {}'.format(walletId))
                continue

            user = User.by_id(client, userId, 'yes')
            if missingDoc == 'individual':
                error, baseDocument = addBasisDocument(user, vbaRequest)
                if error is not None:
                    print('Wallet {}: add individual base doc error: {}'.format(walletId, error['error']))
            else:
                error, baseDocument = addBusinessDocument(user, vbaRequest, walletId)
                if error is not None:
                    print('Wallet {}: add company base doc error: {}'.format(walletId, error['error']))
                

if __name__ == '__main__':
    process()