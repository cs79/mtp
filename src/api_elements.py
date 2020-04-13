# API adapter for Elements allowing generic functionality called by api_shared

# imports
import sqlite3, yaml
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
import warnings

# configuration (per Elements tutorial for now)
HOST_ADDRESS = '127.0.0.1'
RPC_PORT = 18884
RPC_USER = 'user1'
RPC_PASSWORD = 'password1'
BASE_WALLET = '' # default if no name specified
ELEMENTS_ASSET_NAME = 'bitcoin' # configurable at cli when launching chain

# database configuration for R/W of ledger-specific metadata
DB_NAME = 'mtp.db' # should ideally just read this from a config YAML file
conn = sqlite3.connect(DB_NAME)
dbcfg = yaml.load(open('../config/db_config.yaml'), Loader=yaml.SafeLoader)

# functions
def get_rpc_connection(user, password, addr, port, wallet=None):
    '''
    Return an RPC connection object built via bitcoinrpc AuthServiceProxy.
    If "wallet" argument is not None, will create a connection acting on behalf
    of the specified wallet, if it exists.
    '''
    uri = 'http://{}:{}@{}:{}'.format(user, password, addr, port)
    if wallet is not None:
        uri = '{}/wallet/{}'.format(uri, wallet)
    return AuthServiceProxy(uri, timeout=120)

def get_default_rpc(wallet=None):
    '''
    Development convenience for default host / port / user / pass.
    '''
    return get_rpc_connection(RPC_USER, RPC_PASSWORD, HOST_ADDRESS, RPC_PORT,
                              wallet)

# this relies on storage of wallets on server directory where elements is running
def create_elements_wallet(walletname):
    '''
    Creates a new wallet with specified walletname if it does not exist yet.
    '''
    r = get_rpc_connection(RPC_USER, RPC_PASSWORD, HOST_ADDRESS, RPC_PORT,
                           walletname)
    if walletname in r.listwallets():
        warnings.warn('Wallet {} already exists'.format(walletname))
        return {'warning': 'existing wallet'} # compatibility hack
    return r.createwallet(walletname)

def add_user_to_db(userid, guid, conn,
                   tbname_add=dbcfg['ADDRESS_TABLE_NAME'],
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
    r = get_rpc_connection(RPC_USER, RPC_PASSWORD, HOST_ADDRESS, RPC_PORT,
                           wname)
    ctaddr = r.getnewaddress()
    priv = r.dumpprivkey(ctaddr)
    ainfo = r.getaddressinfo(ctaddr)
    ckey = ainfo['confidential_key']
    ucaddr = ainfo['unconfidential']
    # now add entries to SQL
    ledgerid = get_ledgerids(conn, lname='Elements')
    addr_info = (guid, ledgerid, ctaddr, ckey, ucaddr, priv)
    user_info = (guid, ledgerid, wname, None, None) # UTXO model; no keys here
    addr_qry = 'INSERT INTO {} VALUES (?,?,?,?,?,?)'.format(tbname_add)
    user_qry = 'INSERT INTO {} VALUES (?,?,?,?,?)'.format(tbname_lgr)
    c = conn.cursor()
    c.execute(addr_qry, addr_info)
    c.execute(user_qry, user_info)
    conn.commit()
    print('Added user and address information for {} to SQL'.format(wname))

# either need to issue a custom asset when chain starts WITH a reissuance token, or need to create one with a reissuance token, which will need to be tracked by its hex ID

def mint_to_account(amt, dest_acct, conn, gtxid=None, gen_new_addr=True,
                    ct=False,
                    asset=ELEMENTS_ASSET_NAME,
                    tx_tb=dbcfg['TRANSACTION_TABLE_NAME'],
                    bal_tb=dbcfg['BALANCE_TABLE_NAME']):
    '''
    Transfers amt of asset from base account to dest_acct. If an insufficient
    amount of the asset exists, the reissuance token is used to create more.
    If gen_new_addr is True, a new receiving address will be generated for
    dest_acct. If ct is True, a confidential receiving address will be used.
    '''
    # check that asset exists
    r = get_rpc_connection(RPC_USER, RPC_PASSWORD, HOST_ADDRESS, RPC_PORT,
                           BASE_WALLET)
    iss = r.listissuances()
    assets = [i['assetlabel'] for i in iss if 'assetlabel' in i.keys()]
    if not ELEMENTS_ASSET_NAME in assets:
        warnings.warn('Could not find issued asset {}'.format(asset))
        return
    # check that the issuing (base) wallet has sufficient amount of the asset
    bwi = r.getwalletinfo()
    if not bwi['balance'][ELEMENTS_ASSET_NAME] > amt:
        # reissue to base wallet

    return
