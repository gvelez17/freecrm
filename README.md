# freecrm
Simple contact manager to pull and organize contacts from other accounts

cp Dockerfile.general Dockerfile

edit environment settings for your email account and google sheet
if you want to use google sheets, set up a service account and put the credentials into 
a file named.  share the google sheet you want to use with the service account email.
```
.credentials_google_sheets_api.json
```

```
make img
make run
```

In the image
```
python ./getmymail.py
python ./parse_mail.py recent_contacts.csv
```
visit https://docs.google.com/spreadsheets/d/[contact sheet]

