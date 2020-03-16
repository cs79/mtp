# convenience functions for querying info from database

# imports
import yaml
import sqlite3
import pandas as pd
import warnings

# configuration
cfg = yaml.load(open('../config/db_config.yaml'), Loader=yaml.SafeLoader)
conn = sqlite3.connect('../config/{}'.format(cfg['DB_NAME']))

# functions
def get_user_data(conn, tb_name=cfg['LEDGER_USER_TABLE_NAME']):
    '''
    Fetches ledger-specific user information from SQL database.
    '''
    qry = 'SELECT UserID, LedgerID, LedgerUserID FROM {}'.format(tb_name)
    return pd.read_sql(qry, conn)

def get_global_userid(conn, userid, tb_name=cfg['LEDGER_USER_TABLE_NAME']):
    '''
    Fetches Global User ID for a passed ledger-specific User ID.
    '''
    ids = get_user_data(conn=conn, tb_name=tb_name)
    if userid not in ids['LedgerUserID'].values:
        warnings.warn('LedgerUserID {} not found in database'.format(userid))
        return
    return ids[ids['LedgerUserID'] == userid]['UserID'].values[0]

def get_max_userid(conn, tb_name=cfg['USER_TABLE_NAME']):
    '''
    Fetches maximum UserID value in use in SQL database.
    '''
    qry = 'SELECT MAX(UserID) FROM {}'.format(tb_name)
    res = pd.read_sql(qry, conn).iloc[0,0]
    if res is None:
        return 0
    return res

def get_ledgerids(conn, tb_name=cfg['LEDGER_TABLE_NAME'], lname=None):
    '''
    Fetches all ledger IDs, or ID for a specific ledger, from SQL database.
    '''
    if lname is None:
        qry = 'SELECT * FROM {}'.format(tb_name)
        return pd.read_sql(qry, conn)
    else:
        qry = 'SELECT LedgerID \
               FROM {} WHERE LedgerName = \'{}\''.format(tb_name, lname)
        res = pd.read_sql(qry, conn)
        return int(res['LedgerID'][0])

def get_max_txid(conn, tb_name=cfg['TRANSACTION_TABLE_NAME']):
    '''
    Fetches maximum global transaction ID in use in SQL database.
    '''
    qry = 'SELECT MAX(TxGlobalID) FROM {}'.format(tb_name)
    res = pd.read_sql(qry, conn).iloc[0,0]
    if res is None:
        return 0
    return res

def get_user_balance(conn, userid, tb_name=cfg['BALANCE_TABLE_NAME']):
    '''
    Fetches a user's local ledger balance from SQL database.
    '''
    guid = get_global_userid(conn=conn, userid=userid)
    qry = 'SELECT Balance FROM {} WHERE UserID = {}'.format(tb_name, guid)
    res = pd.read_sql(qry, conn)
    if len(res) == 0:
        return 0
    return res.iloc[0,0] # hopefully safe, need to test this though
