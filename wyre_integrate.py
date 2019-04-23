import io, os, traceback
from lib.wyre import wyre

def createWyreApi(credentials):
    account_id = credentials.get('accountId', None)
    api_key = credentials.get('apiKey', None)
    secret_key = credentials.get('apiSecKey', None)
    return wyre(account_id, 'v3', api_key, secret_key)

#export WYRE_ADMIN_ACCOUNTID=AC-T8DT7YJEAP7
#export WYRE_ADMIN_APIKEY=AK-67N6BTRD-WVEUCPTU-93QF4MZQ-VJBV3MAE
#export WYRE_ADMIN_SECRET=SK-ANPR7NW9-TVVZZT3V-DGXVNU33-22HD2Q67
wyreCli = createWyreApi({
    "accountId": os.environ['WYRE_ADMIN_ACCOUNTID'],
    "apiKey": os.environ['WYRE_ADMIN_APIKEY'],
    "apiSecKey": os.environ['WYRE_ADMIN_SECRET']
})

http_code, trans_info = wyreCli.get_trans_info()
print(http_code)
print("\ntrans_info : ")
print(trans_info)
