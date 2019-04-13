from imapclient import IMAPClient
from datetime import date
import os

GMAIL_USERNAME = os.environ.get('GMAIL_USERNAME')
GMAIL_PASSWORD = os.environ.get('GMAIL_PASSWORD')
CONTACTS_FILE = os.environ.get('FREECRM_CONTACTS_FILE') or './contacts.csv'


server = IMAPClient('imap.gmail.com', use_uid=True)
server.login(GMAIL_USERNAME, GMAIL_PASSWORD)


def log_contacts(folder, sent=False):
    server.select_folder(folder)
#	messages = server.search([u'ALL'])
    messages = server.search([u'SINCE', date(2018, 5, 1)])  # ALL to fetch all

    for msgid, data in server.fetch(messages, [b'ENVELOPE']).items():
        try:
            envelope = data[b'ENVELOPE']
            if sent:
                name = envelope.to[0].name or ''
                email = "%s@%s" % (envelope.to[0].mailbox, envelope.to[0].host)
            else:
                from_obj = envelope.reply_to[0] or envelope.from_[0]
                name = from_obj.name or ''
#                        if name == 'Volunteermatch':
#                            import pdb; pdb.set_trace()
                email = "%s@%s" % (from_obj.mailbox, from_obj.host)
            subject = envelope.subject
            subject = subject.replace('\t', ' ')
            with open(CONTACTS_FILE, 'a') as f:
                f.write("%s\t%s\t%s\n" % (name, email, subject))

        except Exception as e:
            print("Error: " + str(e))
            pass


log_contacts('[Gmail]/Sent Mail', sent='true')
log_contacts('[Gmail]/Important')
log_contacts('[Gmail]/Starred')
