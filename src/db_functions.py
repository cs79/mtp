# convenience functions for querying info from database

# imports
import yaml
import sqlite3
import pandas as pd

# configuration
cfg = yaml.load(open('../config/db_config.yaml'), Loader=yaml.SafeLoader)
conn = sqlite3.connect('../config/{}'.format(cfg['DB_NAME']))

# functions
def get_user_data(conn=conn, tb_name=cfg['LEDGER_USER_TABLE_NAME']):
    qry = 'SELECT UserID, LedgerID, LedgerUserID FROM {}'.format(tb_name)
    return pd.read_sql(qry, conn)

def get_max_userid(conn=conn, tb_name=cfg['USER_TABLE_NAME']):
    qry = 'SELECT MAX(UserID) FROM {}'.format(tb_name)
    res = pd.read_sql(qry, conn).iloc[0,0]
    if res is None:
        return 0
    return res

def get_ledgerids(conn=conn, tb_name=cfg['LEDGER_TABLE_NAME'], lname=None):
    if lname is None:
        qry = 'SELECT * FROM {}'.format(tb_name)
    else:
        qry = 'SELECT LedgerID \
               FROM {} WHERE LedgerName = \'{}\''.format(tb_name, lname)
    return pd.read_sql(qry, conn)
