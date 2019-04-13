# freecrm
Simple contact manager to pull and organize contacts from other accounts

cp Dockerfile.general Dockerfile

edit environment settings for your email account and google sheet

make img
make run

python ./getmymail.py
python ./parse_mail.py recent_contacts.csv
visit https://docs.google.com/spreadsheets/d/[contact sheet]
