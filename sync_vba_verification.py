import graypy
import logging
import json, os
from pymongo import MongoClient
from lib.epiapi import epiapi

grayLogger = logging.getLogger('graylog')
grayLogger.setLevel(logging.CRITICAL)
handler = graypy.GELFHandler(os.environ['GRAYLOG_HOST'], int(os.environ['GRAYLOG_PORT']))
grayLogger.addHandler(handler)

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

def getAbnormalVbaRequests():
    vbaRequests = db.vbarequests.find({
        '$and': [
            { 'country': 'US' },
            { 'entityType': { '$exists': False } },
            { 'idNumber': { '$exists': False } },
            { 'dateOfBirth': { '$exists': False } },
            { 'address': { '$exists': False } },
        ]
    })
    for req in vbaRequests:
        yield req

def updateVbaRequest(walletId, data):
    db.vbarequests.update({'walletId':walletId, 'country':'US'}, {'$set':data})

def updateWallet(walletId):
    status, wallet = epiapiCli.get_wallet_by_id(walletId)
    if status == 200:
        if 'vbaVerificationData' in wallet:
            vbaVerificationData = wallet['vbaVerificationData']
            vbaUpdate = {
                'email': vbaVerificationData['email'] if 'email' in vbaVerificationData else None,
                'phoneNumber': vbaVerificationData['phoneNumber'] if 'phoneNumber' in vbaVerificationData else None,
                'ip': vbaVerificationData['ip'] if 'ip' in vbaVerificationData else None,
                'nameCn': vbaVerificationData['nameCn'] if 'nameCn' in vbaVerificationData else None,
                'nameEn': vbaVerificationData['nameEn'] if 'nameEn' in vbaVerificationData else None,
                'idNumber': vbaVerificationData['idNumber'] if 'idNumber' in vbaVerificationData else None,
                'entityType': vbaVerificationData['entityType'] if 'entityType' in vbaVerificationData else None,
                'entityScope': vbaVerificationData['entityScope'] if 'entityScope' in vbaVerificationData else None,
                'companyNameCn': vbaVerificationData['companyNameCn'] if 'companyNameCn' in vbaVerificationData else None,
                'companyNameEn': vbaVerificationData['companyNameEn'] if 'companyNameEn' in vbaVerificationData else None,
                'registrationNumber': vbaVerificationData['registrationNumber'] if 'registrationNumber' in vbaVerificationData else None,
                'dateOfEstablishment': vbaVerificationData['dateOfEstablishment'] if 'dateOfEstablishment' in vbaVerificationData else None,
                'dateOfBirth': vbaVerificationData['dateOfBirth'] if 'dateOfBirth' in vbaVerificationData else None,
                'shopName': vbaVerificationData['shopName'] if 'shopName' in vbaVerificationData else None,
                'merchantIds': vbaVerificationData['merchantIds'] if 'merchantIds' in vbaVerificationData else None,
                'website': vbaVerificationData['website'] if 'website' in vbaVerificationData else None,
                'idDoc': vbaVerificationData['idDoc'] if 'idDoc' in vbaVerificationData else None,
                'coiDoc': vbaVerificationData['coiDoc'] if 'coiDoc' in vbaVerificationData else None,
                'salesDoc': vbaVerificationData['salesDoc'] if 'salesDoc' in vbaVerificationData else None,
                'address': vbaVerificationData['address'] if 'address' in vbaVerificationData else None,
                'countries': vbaVerificationData['countries'] if 'countries' in vbaVerificationData else None,
                'repAddress': vbaVerificationData['repAddress'] if 'repAddress' in vbaVerificationData else None,
                'beneficialOwners': vbaVerificationData['beneficialOwners'] if 'beneficialOwners' in vbaVerificationData else None,
                'expectedMonthlySales': vbaVerificationData['expectedMonthlySales'] if 'expectedMonthlySales' in vbaVerificationData else None,
                'walletType': vbaVerificationData['walletType'] if 'walletType' in vbaVerificationData else None,
                'accountId': vbaVerificationData['accountId'] if 'accountId' in vbaVerificationData else None
            }
            updateVbaRequest(walletId, vbaUpdate)
        else:
            print('No vbaVerificationData in wallet {}'.format(walletId))
    else:
        print('No wallet found with id: {}'.format(walletId))

def process():
    try:
        vbaRequests = getAbnormalVbaRequests()
        for vbaRequest in vbaRequests:
            walletId = vbaRequest.get('walletId', None)
            if walletId is not None:
                updateWallet(walletId)
    except:
        print('internal server error')

if __name__ == '__main__':
    process()