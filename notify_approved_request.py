import threading
from smtplib import SMTP, SMTPException
import logging
import graypy
from pymongo import MongoClient
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from bson.objectid import ObjectId
import json, os

mongoClient = MongoClient(os.environ['VBA_DB_HOST'], int(os.environ['VBA_DB_PORT']))
db = mongoClient.vba_service

grayLogger = logging.getLogger('graylog')
grayLogger.setLevel(logging.CRITICAL)
handler = graypy.GELFHandler(os.environ['GRAYLOG_HOST'], int(os.environ['GRAYLOG_PORT']))
grayLogger.addHandler(handler)

def getFailedToApproveRequests(collection):
    vbaRequests = collection.find({'status': 'APPROVED', 'notified': {'$ne': True}})
    for req in vbaRequests:
        yield req

def markNotified(mongoId, collection):
    collection.update_many({'_id': ObjectId(mongoId)}, {'$set': {'notified':True}})

def mail(subject, message, sender, recipients):
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = sender
        msg['To'] = ', '.join(recipients)
        body = MIMEText(message, 'html')

        msg.attach(body)

        # s = SMTP('localhost')
        s = SMTP('smtp.mandrillapp.com: 587')
        s.starttls()
        s.login('x-border fintech product', 'TIWBeA4tFFiIk8vmBvy9EQ')
        s.sendmail(sender, ', '.join(recipients), msg.as_string())
        s.quit()
        print('Successfully send mail')
        return True
    except SMTPException as err:
        print('Failed to send email')
        print(err)
        grayLogger.critical("unable to send email", extra={'type': 'email_notify_approved_request', 'vbaRequest':message, 'error': err})
        return False

def process():
    threading.Timer(60, process).start()
    for req in getFailedToApproveRequests(db.vbarequests):
        walletId = req.get('walletId')
        status = req.get('status')
        vbaData = req.get('vbaData')
        msg = "<p>wallet : %s</p><p>status : %s</p><p>data : %s</p>" % (walletId, status, json.dumps(vbaData))

        sender = 'noreply@epiapi.com'
        recipients = ['wallets@epiapi.com']
        result = mail('Succeed to approve VBA request', msg, sender, recipients)
        if result is True:
            markNotified(req.get('_id'), db.vbarequests)

if __name__ == '__main__':
    process()
