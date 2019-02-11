import threading
from smtplib import SMTP, SMTPException
import logging
import graypy
from pymongo import MongoClient
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from bson.objectid import ObjectId
import json

mongoClient = MongoClient('13.229.119.114', 27017)
db = mongoClient.vba_service

grayLogger = logging.getLogger('graylog')
grayLogger.setLevel(logging.CRITICAL)
handler = graypy.GELFHandler('52.221.204.21', 12202)
grayLogger.addHandler(handler)

def getFailedToApproveRequests(collection):
    vbaRequests = collection.find({'status': {'$nin': ['APPROVED', 'PENDING', 'WAITING_FOR_APPROVAL']}, 'notified': {'$ne': True}})
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

        s = SMTP('localhost')
        s.sendmail(sender, ', '.join(recipients), msg.as_string())
        s.quit()
        print('Successfully send mail')
        return True
    except SMTPException as err:
        print('Failed to send email')
        grayLogger.critical("unable to send email", extra={'type': 'email_notify_not_approved_request', 'vbaRequest':message, 'error': err})
        return False

def process():
    threading.Timer(60, process).start()
    for req in getFailedToApproveRequests(db.vbarequests):
        walletId = req.get('walletId')
        status = req.get('status')
        vbaData = req.get('vbaData')
        msg = "<p>wallet : %s</p><p>status : %s</p><p>data : %s</p>" % (walletId, status, json.dumps(vbaData))

        sender = 'tantd93@gmail.com'
        recipients = ['tantd93@gmail.com', 'dinhtan3@gmail.com']
        result = mail('Failed to approve VBA request', msg, sender, recipients)
        if result is True:
            markNotified(req.get('_id'), db.vbarequests)

if __name__ == '__main__':
    process()