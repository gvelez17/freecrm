from sheets_lib import Sheet
import sys
import pandas as pd
from merge_lib import merge_overlapping
import os

CONTACT_SHEET = os.environ.get('CONTACT_SHEET_SPECIFIC')

contact_file = sys.argv[1]

df = pd.read_csv(contact_file, sep='\t')
df = df.drop_duplicates('email')

df['name'] = df.name.fillna('')
#df_no_null = df[df.name.notnull()].reset_index(drop=True)
#df_nulls = df[df.name.isnull()].reset_index(drop=True)
#df = pd.concat( [df_no_null, df_nulls])

sheet = Sheet(CONTACT_SHEET)

##############################################################################
# Customize here for your purposes

cw = sheet.get_as_dataframe('CivicWriters', 'A1', 'D200')
cdf = df[df.subject.str.lower().str.contains(r'someone wants') | df.subject.str.lower(
).str.contains(r'civic writers') | df.subject.str.lower().str.contains(r'write for democracy')]
mdf = merge_overlapping(cw, cdf, on=['email'], how='outer')
#mdf = pd.merge(cw, cdf, on=['email'], how='outer')
sheet.upload('CivicWriters', mdf)

##############################################################################
