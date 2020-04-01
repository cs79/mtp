# stand-in SQLite3 database for basic managed services

# imports
# import sqlite3

# configuration
DB_NAME                 = 'mtp.db'
USER_TABLE_NAME         = 'tb_Users'
LEDGER_USER_TABLE_NAME  = 'tb_LedgerUsers'
LEDGER_TABLE_NAME       = 'md_Ledgers'
TRANSACTION_TABLE_NAME  = 'tb_Transactions'
BALANCE_TABLE_NAME      = 'tb_Balances' # for convenience
ADDRESS_TABLE_NAME      = 'tb_Addresses' # for UTXO-based platforms

# table-defining column maps - edit here
USER_TABLE_CMAP         = {'UserID'             : 'integer',
                           'UserName'           : 'text'}
LEDGER_USER_TABLE_CMAP  = {'UserID'             : 'integer',
                           'LedgerID'           : 'integer',
                           'LedgerUserID'       : 'text',
                           'LedgerUserPriv'     : 'text',
                           'LedgerUserPub'      : 'text'}
LEDGER_TABLE_CMAP       = {'LedgerID'           : 'integer',
                           'LedgerName'         : 'text'}
TRANSACTION_TABLE_CMAP  = {'TxGlobalID'         : 'integer',
                           'LedgerID'           : 'integer',
                           'LedgerTxID'         : 'text',
                           'TxOrigin'           : 'integer',
                           'TxDest'             : 'integer',
                           'TxAmount'           : 'real',
                           'Timestamp'          : 'integer'}
BALANCE_TABLE_CMAP      = {'UserID'             : 'integer',
                           'LedgerID'           : 'integer',
                           'Balance'            : 'integer'}
ADDRESS_TABLE_CMAP      = {'UserID'             : 'integer',
                           'LedgerID'           : 'integer',
                           'CTAddress'          : 'text',
                           'ConfidentialKey'    : 'text',
                           'NonCTAddress'       : 'text',
                           'AddressPrivKey'     : 'text'}

# create connection
# conn = sqlite3.connect(DB_NAME)

# helper functions
def cmap_to_query_str(cmap):
    '''
    Converts a column mapping into a query string which can be passed to SQLite.
    '''
    ctypes = list(zip(cmap.keys(), cmap.values()))
    return ', '.join([' '.join(t) for t in ctypes])

# table builder functions
def build_table(conn, tb_name=None, cmap=None):
    '''
    Create empty table at connected database.
    Table columns are identified via a column mapping (cmap) object.
    '''
    c = conn.cursor()
    qry = 'CREATE TABLE {} ({})'.format(tb_name, cmap_to_query_str(cmap))
    c.execute(qry)
    conn.commit()
    print('Created table {}'.format(tb_name))

def build_all(conn):
    '''
    Quickly build the database from available column maps (hardcoded).
    '''
    build_table(conn, USER_TABLE_NAME, USER_TABLE_CMAP)
    build_table(conn, LEDGER_USER_TABLE_NAME, LEDGER_USER_TABLE_CMAP)
    build_table(conn, LEDGER_TABLE_NAME, LEDGER_TABLE_CMAP)
    build_table(conn, TRANSACTION_TABLE_NAME, TRANSACTION_TABLE_CMAP)
    build_table(conn, BALANCE_TABLE_NAME, BALANCE_TABLE_CMAP)
    build_table(conn, ADDRESS_TABLE_NAME, ADDRESS_TABLE_CMAP)
    print('Finished building tables from available definitions')

def empty_table(conn, tb_name=None):
    '''
    Delete all records from a given table.
    '''
    qry = 'DELETE FROM {}'.format(tb_name)
    c = conn.cursor()
    c.execute(qry)
    conn.commit()
    print('Deleted contents of table {}'.format(tb_name))

def empty_all(conn):
    '''
    Quickly empty the entire database so it can be rebuilt.
    '''
    empty_table(conn, USER_TABLE_NAME)
    empty_table(conn, LEDGER_USER_TABLE_NAME)
    empty_table(conn, LEDGER_TABLE_NAME)
    empty_table(conn, TRANSACTION_TABLE_NAME)
    empty_table(conn, BALANCE_TABLE_NAME)
    empty_table(conn, ADDRESS_TABLE_NAME)
    print('Finished emptying records from all tables')

def insert_ledger_md(conn, tb_name=LEDGER_TABLE_NAME):
    '''
    Add master data for ledgers used by multi-token platform (hardcoded).
    '''
    c = conn.cursor()
    ledgers = [(1, 'Elements'),
               (2, 'Iroha')]
    qry = 'INSERT INTO {} VALUES(?, ?)'.format(tb_name)
    c.executemany(qry, ledgers)
    conn.commit()
    print('Inserted master data for ledger table {}'.format(tb_name))

def full_rebuild(conn):
    '''
    Quickly reset the entire database.
    '''
    try:
        empty_all(conn)
    except:
        pass
    try:
        build_all(conn)
    except:
        pass
    try:
        insert_ledger_md(conn)
    except:
        pass
