# API adapter for Elements allowing generic functionality called by api_shared

# imports
import sqlite3, yaml
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
from db_functions import * # own script
import warnings

# configuration (per Elements tutorial for now)
HOST_ADDRESS = '127.0.0.1'
RPC_PORT = 18884
RPC_USER = 'user1'
RPC_PASSWORD = 'password1'
BASE_WALLET = '' # default if no name specified
ELEMENTS_ASSET_NAME = 'bitcoin' # configurable at cli when launching chain
CUSTOM_ASSET = None
CUSTOM_RIT = None

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

def create_asset(asset_amt, token_amt, blind=False):
    '''
    Creates asset_amt of a new custom asset, with token_amt of reissuance
    tokens for that asset.
    If blind == True, the custom asset issuance will be blinded.

    For testing, the asset identifier will be stored in CUSTOM_ASSET,
    and the reissuance token identifier will be stored in CUSTOM_RIT.
    '''
    r = get_rpc_connection(RPC_USER, RPC_PASSWORD, HOST_ADDRESS, RPC_PORT,
                           BASE_WALLET) # issue from base wallet for now
    itx = r.issueasset(asset_amt, token_amt, blind)
    CUSTOM_ASSET = itx['asset']
    CUSTOM_RIT = itx['token']
    return itx

def handle_receiving_address(dest_acct, dest_guid, gen_new_addr, ct, conn,
                             addr_tb=dbcfg['ADDRESS_TABLE_NAME']):
    '''
    Receiving address handler for acct. If gen_new_addr is False, will attempt
    to look up an appropriate (confidential or non-confidential) preexisting
    receiving address; defaults to the last address recorded in SQL.
    If ct is True, will use a confidential receiving address, generating a new
    one if no prior confidential address is found during lookup or if
    gen_new_addr is True.
    '''
    dest_addr = None
    if !gen_new_addr:
        # ensure that we have an available address to use already
        addrs = get_addresses(conn, addr_tb)
        caddrs = addrs[addrs['UserID'] == dest_guid]
        # see if a CT address was requested
        if ct:
            caddrs = caddrs[caddrs['CTAddress'].notnull()]
        if len(caddrs) > 0:
            # just use the last address recorded
            addr_row = caddrs.tail(1)
            # use either CT or non-CT address
            if ct:
                dest_addr = addr_row['CTAddress'].values[0]
            else:
                dest_addr = addr_row['NonCTAddress'].values[0]
        else:
            warnings.warn('No preexisting address to use - generating new')
    # generate a new receiving address if one was not fetched
    if pd.isnull(dest_addr):
        # interact with RPC as receiving wallet
        r2 = get_rpc_connection(RPC_USER, RPC_PASSWORD, HOST_ADDRESS, RPC_PORT,
                                dest_acct)
        newaddr = r2.getnewaddress()
        addrinfo = r2.getaddressinfo(newaddr)
        # extract info to record in SQL
        ctaddr = addrinfo['confidential']
        ckey = addrinfo['confidential_key']
        nctaddr = addrinfo['unconfidential']
        privkey = r2.dumpprivkey(newaddr)
        # set dest_addr based on ct
        if ct:
            dest_addr = ctaddr
        else:
            dest_addr = nctaddr
        # update SQL with the new key
        insert_address(conn, dest_guid, lid, ctaddr, ckey, nctaddr, privkey,
                       addr_tb)
    return dest_addr


def mint_to_account(amt, dest_acct, conn, gtxid=None, gen_new_addr=True,
                    ct=False,
                    asset=CUSTOM_ASSET,
                    tx_tb=dbcfg['TRANSACTION_TABLE_NAME'],
                    bal_tb=dbcfg['BALANCE_TABLE_NAME'],
                    addr_tb=dbcfg['ADDRESS_TABLE_NAME']):
    '''
    Transfers amt of asset from base account to dest_acct. If an insufficient
    amount of the asset exists, the reissuance token is used to create more.
    If gen_new_addr is True, a new receiving address will be generated for
    dest_acct. If ct is True, a confidential receiving address will be used.
    '''
    # set up some internal reference variables
    reissued = False
    lid = get_ledgerids(conn, lname='Elements')
    base_bal = get_user_balance(conn, BASE_WALLET, bal_tb)
    dest_bal = get_user_balance(conn, dest_acct, bal_tb)
    base_guid = get_global_userid(conn, BASE_WALLET)
    dest_guid = get_global_userid(conn, dest_acct)
    # check that asset exists
    r = get_rpc_connection(RPC_USER, RPC_PASSWORD, HOST_ADDRESS, RPC_PORT,
                           BASE_WALLET)
    iss = r.listissuances()
    assets = [i['assetlabel'] for i in iss if 'assetlabel' in i.keys()]
    if not asset in assets:
        warnings.warn('Could not find issued asset {}'.format(asset))
        return
    # set up receiving address for dest_acct according to passed params
    dest_addr = handle_receiving_address(dest_acct, dest_guid, gen_new_addr,
                                         ct, conn, addr_tb)
    # check that the issuing (base) wallet has sufficient amount of the asset
    bwi = r.getwalletinfo()
    if not bwi['balance'][asset] > amt:
        # reissue to base wallet
        rtx = r.reissueasset(asset, amt)
        # confirm that the transaction was not abandoned
        rtxdata = r.gettransaction(rtx['txid'])
        rstx = [i for i in rtxdata['details'] if i['asset'] == asset
                and i['category'] == 'send'][0]
        if rstx['abandoned']:
            warnings.warn('Transaction {} was abandoned - aborting'.format(rtx['txid']))
            return
        reissued = True
        # if the reissuance succeeded, log this in SQL as well
        record_transaction(conn, gtxid, lid, rtx['txid'], 'MINT',
                           rstx['address'], amt, rtxdata['timereceived'],
                           'Top up base wallet', tx_tb) # or rtxdata['time']
        update_balance(conn, base_guid, lid, base_bal+amt, bal_tb)
    # base wallet should now have sufficient custom asset to "mint" to account
    memo = 'Minting of asset to account'
    mtx = r.sendtoaddress(dest_addr, amt, memo, '', False, False, 1, 'UNSET',
                          asset)
    # generate to address to confirm (1) block
    r.generatetoaddress(1, dest_addr)
    # confirm that transaction was not abandoned
    mtxdata = r.gettransaction(mtx)
    if mtxdata['details'][0]['abandoned']:
        warnings.warn('Transaction {} was abandoned - aborting'.format(mtx))
        return
    # if the transaction wasn't abandoned, update the SQL database as well
    if reissued:
        # refresh base balance
        base_bal = get_user_balance(conn, BASE_WALLET, bal_tb)
        # ensure correct gtxid if it was passed
        if gtxid is not None
            gtxid += 1
    record_transaction(conn, gtxid, lid, mtx, 'MINT', dest_acct, amt,
                       mtxdata['timereceived'], memo, tx_tb)
    update_balance(conn, base_guid, lid, base_bal-amt, bal_tb)
    update_balance(conn, dest_guid, lid, dest_bal+amt, bal_tb)
    return

def transfer_asset(from_acct, dest_acct, amt, conn, memo=None, gtxid=None,
                   gen_new_addr=True, ct=False, asset=CUSTOM_ASSET,
                   tx_tb=dbcfg['TRANSACTION_TABLE_NAME'],
                   bal_tb=dbcfg['BALANCE_TABLE_NAME'],
                   addr_tb=dbcfg['ADDRESS_TABLE_NAME']):
    '''
    Transfer amt of asset from from_acct to dest_acct, using a new receiving
    address and/or confidential receiving address if requested.
    '''
    # set up internal reference variables
    lid = get_ledgerids(conn, lname='Elements')
    from_bal = get_user_balance(conn, from_acct, bal_tb)
    dest_bal = get_user_balance(conn, dest_acct, bal_tb)
    from_guid = get_global_userid(conn, from_acct)
    dest_guid = get_global_userid(conn, dest_acct)
    # send requests as sending wallet
    r = get_rpc_connection(RPC_USER, RPC_PASSWORD, HOST_ADDRESS, RPC_PORT,
                           from_acct)
    # prep receiving address per parameters
    dest_addr = handle_receiving_address(dest_acct, dest_guid, gen_new_addr,
                                         ct, conn, addr_tb)
    # send from from_acct to the specified dest_addr
    tx = r.sendtoaddress(dest_addr, amt, memo, '', False, False, 1, 'UNSET',
                         asset)
    # generate to address to confirm (1) block
    r.generatetoaddress(1, dest_addr)
    # confirm that transaction was not abandoned
    # (will fail with JSONRPCException if insufficient funds)
    txdata = r.gettransaction(tx)
    if txdata['details'][0]['abandoned']:
        warnings.warn('Transaction {} was abandoned - aborting'.format(tx))
        return
    # if the transaction wasn't abandoned, update the SQL database as well
    record_transaction(conn, gtxid, lid, tx, from_acct, dest_acct, amt,
                       txdata['timereceived'], memo, tx_tb)
    update_balance(conn, from_guid, lid, from_bal-amt, bal_tb)
    update_balance(conn, dest_guid, lid, dest_bal+amt, bal_tb)
    return
