# API adapter for Elements allowing generic functionality called by api_shared

# imports
import sqlite3
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
import warnings

# configuration (per Elements tutorial for now)
RPC_PORT = 18884
RPC_USER = 'user1'
RPC_PASSWORD = 'password1'
BASE_WALLET = '' # default if no name specified
ELEMENTS_ASSET_NAME = 'bitcoin' # configurable at cli when launching chain

# database configuration for R/W of ledger-specific metadata
DB_NAME = 'mtp.db' # should ideally just read this from a config YAML file
conn = sqlite3.connect(DB_NAME)

# functions
def get_rpc_connection(user, password, port, wallet=None):
    '''
    Return an RPC connection object built via bitcoinrpc AuthServiceProxy.
    If "wallet" argument is not None, will create a connection acting on behalf
    of the specified wallet, if it exists.
    '''
    uri = 'http://{}:{}@127.0.0.1:{}'.format(user, password, port)
    if wallet is not None:
        uri = '{}/wallet/{}'.format(uri, wallet)
    return AuthServiceProxy(uri, timeout=120)

# this relies on storage of wallets on server directory where elements is running
def create_elements_wallet(walletname):
    '''
    Creates a new wallet with specified walletname if it does not exist yet.
    '''
    r = get_rpc_connection(RPC_USER, RPC_PASSWORD, RPC_PORT, walletname)
    if walletname in r.listwallets():
        warnings.warn('Wallet {} already exists'.format(walletname))
        return {'warning': 'existing wallet'} # compatibility hack
    return r.createwallet(walletname)

def add_user_to_db(userid, guid, conn, \
                   tbname_add=dbcfg['ADDRESS_TABLE_NAME'], \
                   tbname_lgr=dbcfg['LEDGER_USER_TABLE_NAME']):
    '''
    Add a user to Elements by creating a wallet for them, and to shared DB.
    Also generate initial receiving address and store privkey for recovery.
    '''
    wname = '{}_ewallet'.format(userid) # as a default convention
    wal = create_elements_wallet(wname)
    if wal['warning'] != '':
        warnings.warn('Something went wrong with wallet creation: \
                       {}'.format(wal['warning']))
        return
    # if we have created a new wallet, get a new address / privkey to store
    r = get_rpc_connection(RPC_USER, RPC_PASSWORD, RPC_PORT, wname)
    addr = r.getnewaddress()
    priv = r.dumpprivkey(addr)
    # now add entries to SQL
    ledgerid = get_ledgerids(conn, lname='Elements')
    addr_info = (guid, ledgerid, addr, priv)
    user_info = (guid, ledgerid, wname, None, None) # UTXO model; no keys here
    addr_qry = 'INSERT INTO {} VALUES (?,?,?,?)'.format(tbname_add)
    user_qry = 'INSERT INTO {} VALUES (?,?,?,?,?)'.format(tbname_lgr)
    c = conn.cursor()
    c.execute(addr_qry, addr_info)
    c.execute(user_qry, user_info)
    conn.commit()
    print('Added user and address information for {} to SQL'.format(wname))
