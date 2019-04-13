import numpy as np
import pandas as pd
from warnings import warn


def bnull(ser):
    """
    shorthand for checking a string series for blanks and nulls
    returns a mask that is True for any row in the original series that was blank or null
    Sometimes series of type Object will contain mixed types
    """
    if ser.dtype == np.dtype('O'):
        # note: avoid astype(str) when using the value
        return ser.isnull() | (ser.str.strip().astype(str) == '')
        # it converts NaN to 'nan'
    else:
        return ser.isnull()


def merge_overlapping(df1, df2, how='outer', on=[], prefer_right=[], label=''):
    """
    Merge two dataframes on the given merge columns
    for overlapping columns, prefer the first dataframe if not null
    """
    # use sorted here other wise the result dataframe column order may change and lead to md5 change
    shared_keys = sorted(set(df1.keys()).intersection(set(df2.keys())))

    for col in on:
        shared_keys.remove(col)
        dt1 = df1[col].dtype
        dt2 = df2[col].dtype

    # no matter if df2 should be uniqued or not, analyze the duplications in it
    df2_uniq = df2.drop_duplicates(subset=on)

    # make sure the first of the merge cols is present (non-blank, and not unknown val) as this is normally the primary merge col
    df2 = df2[~bnull(df2[on[0]]) & ~df2[on[0]].isin(
        ['pending', 'unknown', 'n/a', 'unavailable'])]

    if len(df1) == 0:
        return df1, df1, df1
    #

    df = df1.merge(df2, how, on=on, indicator=True)

    for col in shared_keys:
        try:
            if col in prefer_right:
                # prefer the non-blank-or-null value; if both are bnull, prefer blank to null
                prefer_right_mask = ~bnull(
                    df[col + '_y']) | df[col + '_x'].isnull()

                # this is application specific - sometimes we want to keep blank cols from the right
                if enforce_right_col in df:
                    prefer_right_mask |= df[enforce_right_col] == enforce_right_val
                elif enforce_right_col + '_y' in df:
                    prefer_right_mask |= df[enforce_right_col +
                                            '_y'] == enforce_right_val

                df[col] = np.where(prefer_right_mask,
                                   df[col + '_y'],
                                   df[col + '_x'])
            else:
                df[col] = np.where(~bnull(df[col + '_x']) | df[col + '_y'].isnull(),
                                   df[col + '_x'],
                                   df[col + '_y'])
            df = df.drop([col + '_x', col + '_y'], axis=1)
        except Exception as e:
            warn('ERROR on shared key %s : %s' % (col, str(e)))

    pd.set_option('display.max_colwidth', -1)

    return df
