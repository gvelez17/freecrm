"""
Open Source LGPL 1.0
"""

import httplib2
import os
from googleapiclient import discovery
from googleapiclient.errors import HttpError
import datetime

from merge_lib import merge_overlapping

import pandas as pd
import numpy as np
from oauth2client.service_account import ServiceAccountCredentials
import string

if os.environ.get('socks_proxy'):
    # only if you need to use a proxy
    # https://github.com/httplib2/httplib2/issues/22
    import socks

    socks.setdefaultproxy(socks.PROXY_TYPE_SOCKS5, '127.0.0.1', 8080)
    socks.wrapmodule(httplib2)

SCOPES = 'https://www.googleapis.com/auth/spreadsheets'


def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the storcated credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """

    path = os.path.expanduser('~/.credentials/google_sheets_api.json')

    if os.path.exists(path):
        credentials = ServiceAccountCredentials.from_json_keyfile_name(
            path, SCOPES)
    else:
        print('File ~/.credentials/google_sheets_api.json not found')
        exit(1)

    return credentials


def get_service():
    credentials = get_credentials()

    http = credentials.authorize(httplib2.Http())
    discovery_url = 'https://sheets.googleapis.com/$discovery/rest?version=v4'
    service = discovery.build(
        'sheets', 'v4', http=http, discoveryServiceUrl=discovery_url, cache_discovery=False)
    return service


def clear(spreadsheet_id, sheet_name):

    service = get_service()

    # clear this sheet first
    # use A:Z to clear all the cells
    service.spreadsheets().values().clear(
        spreadsheetId=spreadsheet_id, range="'%s'!A:Z" % sheet_name, body={}).execute()


def hyperlink(href, text):
    """
    for put a link in google sheet
    """
    return '=HYPERLINK("%s", "%s")' % (href.replace('"', '%22'), text)


class Sheet:
    """
    To give permission to this API, share the doc with:
        robot-879@leafy-courier-188303.iam.gserviceaccount.com
    """

    currency_format = {'type': 'CURRENCY', 'pattern': '$#,#'}
    number_format = {'type': 'NUMBER', 'pattern': '#,#'}
    percent_format = {'type': 'PERCENT', 'pattern': '##.00%'}

    def __init__(self, doc_id):
        self.doc_id = doc_id
        self.service = get_service()
        self.sheet_metadata = self.service.spreadsheets().get(
            spreadsheetId=self.doc_id).execute()

    def copy_to(self, title, destination_doc_id):
        """
        copy a tab into a new file
        """

        copy_sheet_to_another_spreadsheet_request_body = {
            'destination_spreadsheet_id': destination_doc_id,
        }

        sheet_id = self.get_sheet_id(title)

        request = self.service.spreadsheets().sheets().copyTo(spreadsheetId=self.doc_id, sheetId=sheet_id,
                                                              body=copy_sheet_to_another_spreadsheet_request_body)
        request.execute()

    def load(self, title):
        # clear this sheet first
        resp = self.service.spreadsheets().values().get(
            spreadsheetId=self.doc_id, range="'%s'" % title).execute()

        if 'values' in resp:
            values = resp['values']

            width = 0

            for row in values:
                if len(row) > width:
                    width = len(row)

            # fill blank with None
            adjusted_content = []
            for row in values:
                length_diff = width - len(row)
                row += [None] * length_diff
                adjusted_content.append(row)

            header = adjusted_content[0]
            content = adjusted_content[1:]
            df = pd.DataFrame(content, columns=header)

            return df
        else:
            return pd.DataFrame()

    def message(self, title, message):
        """
        put a message on this tab
        """
        df = pd.DataFrame([message], columns=[''])
        self.upload(title, df)

    def get_as_dataframe(self, title, from_cell, to_cell):
        arr_list = self.get_all_values(title, from_cell, to_cell)
        columns = arr_list[0]
        arr_list = arr_list[1:]
        for j in range(0, len(arr_list)):
            pad_num = len(columns) - len(arr_list[j])
            arr_list[j] = arr_list[j] + [''] * pad_num
        return pd.DataFrame(arr_list, columns=columns)

    def get_all_values(self, title, from_cell, to_cell):
        request = self.service.spreadsheets().values().get(
            spreadsheetId=self.doc_id,
            range="'%s'!%s:%s" % (title, from_cell, to_cell),
            valueRenderOption="UNFORMATTED_VALUE")
        response = request.execute()
        return response.get('values', None)

    def get_cell_value(self, title, cell_range):
        request = self.service.spreadsheets().values().get(
            spreadsheetId=self.doc_id,
            range="'%s'!%s:%s" % (title, cell_range, cell_range),
            valueRenderOption='UNFORMATTED_VALUE')
        response = request.execute()
        if 'values' in response:
            return response['values'][0][0]
        else:
            return None

    def update_cell(self, title, cell_range, value):

        body = {
            'values': [
                [value]
            ]
        }

        existing = self.get_cell_value(title, cell_range)

        if existing is None:
            self.service.spreadsheets().values().update(
                spreadsheetId=self.doc_id,
                range="'%s'!%s:%s" % (title, cell_range, cell_range),
                valueInputOption='USER_ENTERED',
                body=body).execute()
        elif existing != value:
            print("Error")

    def update_cell_by_row_and_column(self, title, row_label, column_label, value):
        cell_range = self.locate_cell(title, row_label, column_label)
        self.update_cell(title, cell_range, value)

    def format_cell_by_row_and_column(self, title, row_label, column_label, format):
        """
        :param format: a json, eg:

        {'type': 'CURRENCY'}
        {'type': 'PERCENT', 'pattern': '##.00%'}

        """
        row_index = self.get_row_index(title, row_label)
        column_index = self.get_column_index(title, column_label)

        sheet_id = self.get_sheet_id(title)

        self.service.spreadsheets().batchUpdate(
            spreadsheetId=self.doc_id, body={
                'requests': [
                    {'repeatCell': {
                        'range': {'sheetId': sheet_id,
                                  "startColumnIndex": column_index, "endColumnIndex": column_index + 1,
                                  "startRowIndex": row_index, "endRowIndex": row_index + 1,
                                  },
                        'cell': {'userEnteredFormat': {'numberFormat': format}},
                        'fields': 'userEnteredFormat.numberFormat',
                    }}
                ]
            }).execute()

    def upload(self, title, df):

        print('Posting to Google Sheet [%s]' % title)
        for col in df.keys():
            try:
                df[col] = df[col].fillna('')
            except:
                pass
        df = df.copy()

        if len(df) == 0:
            return self.message(title, "There are no rows here.")

        # convert date object into string object for google sheet api
        for column in df.columns:

            # if column == 'election_date':
            #     import pdb
            #     pdb.set_trace()

            for i in range(len(df)):
                value = df[column].iloc[i]
                if isinstance(value, pd.tslib.Timestamp) or isinstance(value, datetime.date):
                    print('Convert column %s into string' % column)
                    df[column] = pd.to_datetime(df[column]).dt.strftime(
                        '%Y-%m-%d').str.replace('NaT', '')
                    break

        headers = [df.columns.tolist()]
        values = df.values.tolist()

        data = [
            {
                'range': "'%s'" % title,
                'values': headers + values
            },
            # Additional ranges to update ...
        ]
        body = {
            'valueInputOption': 'USER_ENTERED',
            'data': data
        }

        # clear this sheet first
        self.service.spreadsheets().values().clear(
            spreadsheetId=self.doc_id, range="'%s'" % title, body={}).execute()

        # then fill values
        self.service.spreadsheets().values().batchUpdate(
            spreadsheetId=self.doc_id, body=body).execute()

        sheet_id = self.get_sheet_id(title)

        self.service.spreadsheets().batchUpdate(
            spreadsheetId=self.doc_id, body={
                'requests': [
                    # lock first line
                    {'updateSheetProperties': {
                        'properties': {'sheetId': sheet_id, 'gridProperties': {'frozenRowCount': 1}},
                        'fields': 'gridProperties.frozenRowCount',
                    }},

                    # bold first line
                    {'repeatCell': {
                        'range': {'sheetId': sheet_id, "startRowIndex": 0, "endRowIndex": 1},
                        'cell': {'userEnteredFormat': {'textFormat': {'bold': True}}},
                        'fields': 'userEnteredFormat.textFormat.bold',
                    }}
                ]
            }).execute()

        print('Google Sheet [%s] updated' % title)

    def upsert(self, title, df):
        # TODO this would be nice to have, add the sheet if it doesnt' exist
        try:
            self.upload(title, df)
        except HttpError:
            self.add_sheet(title)
            self.upload(title, df)

    def add_sheet(self, title):
        # TODO this not working yet

        self.service.spreadsheets().batchUpdate(
            spreadsheetId=self.doc_id, body={
                'requests': [
                    {
                        'addSheet': {
                            'properties': {
                                'title': title,
                            },
                        }
                    }
                ]
            }).execute()

    def format_as_currency(self, title, column_index):
        sheet_id = self.get_sheet_id(title)

        self.service.spreadsheets().batchUpdate(
            spreadsheetId=self.doc_id, body={
                'requests': [
                    {'repeatCell': {
                        'range': {'sheetId': sheet_id, "startColumnIndex": column_index, "endColumnIndex": column_index + 1},
                        'cell': {'userEnteredFormat': {'numberFormat': {'type': 'CURRENCY'}}},
                        'fields': 'userEnteredFormat.numberFormat',
                    }}
                ]
            }).execute()

    def format_as_percent(self, title, column_index):
        sheet_id = self.get_sheet_id(title)

        self.service.spreadsheets().batchUpdate(
            spreadsheetId=self.doc_id, body={
                'requests': [
                    {'repeatCell': {
                        'range': {'sheetId': sheet_id, "startColumnIndex": column_index, "endColumnIndex": column_index + 1},
                        'cell': {'userEnteredFormat': {'numberFormat': {'type': 'PERCENT', 'pattern': '##.00%'}}},
                        'fields': 'userEnteredFormat.numberFormat',
                    }}
                ]
            }).execute()

    def update_doc_title(self, new_title):
        # todo: this is not working yet
        self.service.spreadsheets().batchUpdate(
            spreadsheetId=self.doc_id, body={
                'requests': [
                    {'updateSheetProperties': {
                        'properties': {'title': new_title},
                    }},

                ]
            }).execute()

    def validate(self, title, column_index, valid_values):
        """
        google sheet
        """

        sheet_id = self.get_sheet_id(title)

        values = [{"userEnteredValue": x} for x in valid_values]

        self.service.spreadsheets().batchUpdate(
            spreadsheetId=self.doc_id, body={
                'requests': [
                    {'setDataValidation': {
                        'range': {'sheetId': sheet_id, "startRowIndex": 1, "startColumnIndex": column_index, "endColumnIndex": column_index + 1},
                        'rule': {
                            'condition': {
                                "type": 'ONE_OF_LIST',
                                "values": values
                            },
                            'showCustomUi': True,
                            "strict": True
                        },
                    }},
                ]
            }).execute()

    def get_sheet_id(self, title):
        """
        The the sheet/tab id
        """
        sheet_id = 0
        for sheet in self.sheet_metadata['sheets']:
            if sheet['properties']['title'] == title:
                sheet_id = sheet['properties']['sheetId']
                break
        return sheet_id

    def url(self, title=None):
        if title is None:
            return "https://docs.google.com/spreadsheets/d/%s" % self.doc_id
        else:
            return "https://docs.google.com/spreadsheets/d/%s/edit#gid=%s" % (self.doc_id, self.get_sheet_id(title))

    def preserve(self, sheet_title, new_sheet_df, keys, columns):
        """
        Load a sheet, and attach the preserved values to new_sheet_df then return the new dataframe.
        An example is to join on keys=['candidate_id'], attache on columns=['action', 'action notes']
        """
        # load sheet
        manually_confirmed = self.load(sheet_title)

        if len(manually_confirmed) > 0:
            # add columns if missed
            for c in columns:
                if c not in manually_confirmed:
                    manually_confirmed[c] = ''

            # make sure all the keys are in the loaded sheet, if you just changed the dataframe,
            # the key will not be at the sheet yet. In this case, skip
            keys_available = True

            for c in keys:
                if c not in manually_confirmed:
                    keys_available = False
                    break

            if keys_available:
                # select non-blank rows
                manually_confirmed = manually_confirmed[manually_confirmed[columns].any(
                    axis=1)]

                # merge with new_sheet_df
                new_sheet_with_preserved_values = merge_overlapping(new_sheet_df,
                                                                    manually_confirmed[keys + columns], on=keys, how='left')
                new_sheet_with_preserved_values.drop(
                    '_merge', axis=1, inplace=True)
            else:
                new_sheet_with_preserved_values = new_sheet_df

        else:
            new_sheet_with_preserved_values = new_sheet_df

        # add columns if missed
        for c in columns:
            if c not in new_sheet_with_preserved_values:
                new_sheet_with_preserved_values[c] = ''

        return new_sheet_with_preserved_values

    def select_confirmed(self, title, df, keys):
        """
        select where action is 'confirmed'
        """
        manually_confirmed = self.load(title)
        manually_confirmed = manually_confirmed[manually_confirmed['action'] == 'confirmed']

        print('%s manually confirmed rows in %s' %
              (len(manually_confirmed), title))

        if len(manually_confirmed) > 0:

            # make sure keys are in the same datatype
            for k in keys:
                df[k] = num_to_str(df[k])
                manually_confirmed[k] = num_to_str(manually_confirmed[k])

            df = merge_overlapping(
                df, manually_confirmed[keys], on=keys, unique=False, how='left')

            # select merged rows
            df = df[df['_merge'] == 'both']

            df.drop(['_merge'], axis=1, inplace=True)

            return df
        else:
            return pd.DataFrame()

    def get_column_index(self, title, column_label):
        df = self.load(title)
        column_index = df.iloc[0].index.tolist().index(column_label)
        return column_index

    def get_row_index(self, title, row_label):

        df = self.load(title)

        # the first column matches row_label
        matching_rows = df[df.iloc[:, 0].str.lower() == row_label.lower()]

        if len(matching_rows) == 1:

            row_index = df[df.iloc[:, 0].str.lower() ==
                           row_label.lower()].index[0]

            # plus one because we skiped header
            row_index += 1

            # google sheet needs int not numpy.int
            if isinstance(row_index, np.generic):
                row_index = np.asscalar(row_index)

            return row_index

        else:
            print('%d rows match the row label %s, please check' %
                  (len(matching_rows), row_label))
            exit(1)

    def locate_cell(self, title, row_label, column_label):
        """
        Locate a cell by it's row label and column label
        return the location in A1 notation.
        """

        # need to update the code when we had more than 26 columns
        column = string.ascii_uppercase[self.get_column_index(
            title, column_label)]

        # +1 because A1 notation starts from 1 and google api (get_row_index) starts from 0
        row = self.get_row_index(title, row_label) + 1

        return '%s%s' % (column, row)
