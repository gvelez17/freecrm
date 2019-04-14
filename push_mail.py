import pdb
from sheets_lib import Sheet
import sys
import pandas as pd
import os

CONTACT_SHEET = os.environ.get('CONTACT_SHEET')

contact_file = sys.argv[1]

df = pd.read_csv(contact_file, sep='\t')
df = df.drop_duplicates('email')

df['name'] = df.name.fillna('')
#df_no_null = df[df.name.notnull()].reset_index(drop=True)
#df_nulls = df[df.name.isnull()].reset_index(drop=True)
#df = pd.concat( [df_no_null, df_nulls])

sheet = Sheet(CONTACT_SHEET)

sheet.upload('raw', df)

print("Visit https://docs.google.com/spreadsheets/d/%s" % CONTACT_SHEET)
