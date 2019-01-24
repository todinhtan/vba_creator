from pymongo import MongoClient
import threading
import requests
import pinyin

core_url = '3.0.150.148:8080'

client = MongoClient('172.31.24.67', 27017)
db = client.vba_service
def getPendingRequest():
    vbaRequests = db.vbarequests.find({"country":"AU", "status":"PENDING"})
    for req in vbaRequests:
        yield req

def getNABVBA():
    nabVBA = db.nab_vba.find_one({"status":"unused"})
    print("nabVBA:")
    print(nabVBA)
    return nabVBA

def updateVBA(req, vba):
    db.vbarequests.update({'_id':req.get('_id')}, {'$set':{'vbaData':req.get('vbaData'), 'status':'APPROVED'}})
    db.nab_vba.update({'_id':vba.get('_id')}, {'$set':{'status':'in-used'}})

def createVBA():
    threading.Timer(5 * 60, createVBA).start()
    for req in getPendingRequest():
        nabVBA = getNABVBA()
        if nabVBA is None:
            print("no more NAB VBA")
            break
        beneficiaryName = pinyin.get(req.get("nameCn"), format="strip", delimiter=" ") if (req.get('nameCn', None) != '' and req.get('nameCn', None) != None) else req.get("nameEn")
        # beneficiaryName =  req.get('nameEn') if req.get('nameEn',None) != "" and req.get('nameEn',None) is not None \
        #     else nabVBA.get('nameCn', None)
        req['vbaData'] = {
            "bankAddress": "Level 14 500 Bourke St, Melbourne, VIC 3000",
            "bankName": "National Australia Bank Limited",
            "accountNumber": nabVBA.get('accountNumber'),
            "routingNumber": nabVBA.get('routingNumber'),
            "beneficiaryName": beneficiaryName
        }
        updateVBA(req,nabVBA)
        # callbackUpdateCoreWallet(walletId=req.get('walletId'), vbaData=req['vbaData'], sessionId=req.get('sessionId'))

if __name__ == '__main__':
    createVBA()
