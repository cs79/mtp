# stand-in SQLite3 database for basic managed services

# imports
import sqlite3

# configuration
DB_NAME                 = 'mtp.db'
USER_TABLE_NAME         = 'tb_Users'
LEDGER_USER_TABLE_NAME  = 'tb_LedgerUsers'
LEDGER_TABLE_NAME       = 'md_Ledgers'
TRANSACTION_TABLE_NAME  = 'tb_Transactions'

# table-defining column maps - edit here
USER_TABLE_CMAP         = {'UserID'         : 'integer',
                           'UserName'       : 'text'}
LEDGER_USER_TABLE_CMAP  = {'UserID'         : 'integer',
                           'LedgerID'       : 'integer',
                           'LedgerUserID'   : 'text',
                           'LedgerUserPriv' : 'text',
                           'LedgerUserPub'  : 'text'}
LEDGER_TABLE_CMAP       = {'LedgerID'       : 'integer',
                           'LedgerName'     : 'text'}
TRANSACTION_TABLE_CMAP  = {'TxGlobalID'     : 'integer',
                           'LedgerID'       : 'integer',
                           'LedgerTxID'     : 'text',
                           'TxOrigin'       : 'integer',
                           'TxDest'         : 'integer',
                           'TxAmount'       : 'real',
                           'Timestamp'      : 'integer'}

# create connection
conn = sqlite3.connect(DB_NAME)

# helper functions
def cmap_to_query_str(cmap):
    '''
    Converts a column mapping into a query string which can be passed to SQLite.
    '''
    ctypes = list(zip(cmap.keys(), cmap.values()))
    return ', '.join([' '.join(t) for t in ctypes])

# table builder functions
def build_table(conn=conn, tb_name=None, cmap=None):
    '''
    Create empty table at connected database.
    Table columns are identified via a column mapping (cmap) object.
    '''
    c = conn.cursor()
    qry = 'CREATE TABLE {} ({})'.format(tb_name, cmap_to_query_str(cmap))
    c.execute(qry)
    conn.commit()
    print('Created table {}'.format(tb_name))

def build_all(conn=conn):
    '''
    Quickly build the database from available column maps (hardcoded).
    '''
    build_table(conn, USER_TABLE_NAME, USER_TABLE_CMAP)
    build_table(conn, LEDGER_USER_TABLE_NAME, LEDGER_USER_TABLE_CMAP)
    build_table(conn, LEDGER_TABLE_NAME, LEDGER_TABLE_CMAP)
    build_table(conn, TRANSACTION_TABLE_NAME, TRANSACTION_TABLE_CMAP)
    print('Finished building tables from available definitions')

def insert_ledger_md(conn=conn, tb_name=LEDGER_TABLE_NAME):
    '''
    Add master data for ledgers used by multi-token platform (hardcoded).
    '''
    c = conn.cursor()
    ledgers = [(1, 'Elements'),
               (2, 'Iroha')]
    qry = 'INSERT INTO {} VALUES(?, ?)'.format(tb_name)
    c.executemany(qry, ledgers)
    print('Inserted master data for ledger table {}'.format(tb_name))

# execute functions so that this script can easily be run
build_all()
insert_ledger_md()
