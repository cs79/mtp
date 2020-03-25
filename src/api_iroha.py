# API adapter for Iroha allowing generic functionality called by api_shared

# imports
import sqlite3
from db_functions import * # own script
import pandas as pd
from iroha import Iroha, IrohaGrpc, IrohaCrypto
from iroha.primitive_pb2 import can_set_my_account_detail
import hashlib, binascii
import warnings, re

# configuration (per Iroha example guide for now)
admin_private_key = 'f101537e319568c765b2cc89698325604991dca57b9716b58016b253506cab70'
# user_private_key = IrohaCrypto.private_key()
# user_public_key = IrohaCrypto.derive_public_key(user_private_key)
iroha = Iroha('admin@test')
net = IrohaGrpc()

dbcfg = yaml.load(open('../config/db_config.yaml'), Loader=yaml.SafeLoader)
dltcfg = yaml.load(open('dltcfg.yaml'), Loader=yaml.SafeLoader)
conn = sqlite3.connect('../config/{}'.format(dbcfg['DB_NAME']))

UID_PAT = '[a-z0-9]+@[a-z0-9]+'
LEDGER_ASSET = '{}#{}'.format(dltcfg['ASSET_NAME'], dltcfg['IROHA_DOMAIN'])

# functions
def get_iroha_user_info(userid):
    '''
    Queries Iroha blockchain for info about userid.
    '''
    qry = iroha.query('GetAccount', account_id=userid)
    IrohaCrypto.sign_query(qry, admin_private_key)
    return net.send_query(qry)

def create_iroha_user_account(userid, pubkey):
    '''
    Add a new userid to Iroha blockchain.
    '''
    # split userid string into account and domain info
    uid = userid.split('@')
    cmd = [iroha.command('CreateAccount', account_name=uid[0], domain_id=uid[1],
                         public_key=pubkey)]
    tx = iroha.transaction(cmd)
    IrohaCrypto.sign_transaction(tx, admin_private_key)
    net.send_tx(tx)
    return [s for s in net.tx_status_stream(tx)]

# pattern should be something like:
# - check if userid already exists in SQL, if so, throw
# - check if userid already exists in DLT, if so, skip next 2.5 steps
# - prep the DLT transaction and submit it
# - somehow await confirmation / test within some amount of time if accepted
# - if accepted on DLT, prep SQL and insert new record as appropriate
# QUESTION: WHAT IF THIS USER IS "THE SAME" AS A USER THAT EXISTS ON A DIFFERENT LEDGER?
def add_user_to_db(userid, guid, conn,
                   tb_name=dbcfg['LEDGER_USER_TABLE_NAME']):
    '''
    Add a user to the Iroha ledger and the shared database.
    N.B. userid should be in proper Iroha format, e.g. "user@domain".
    The guid value (global platform-level user ID) should be passed from
    the shared API, which will generate it.
    '''
    # check correct userid format
    assert re.match(UID_PAT, userid) is not None, 'invalid userid format'
    # empty placeholders for privkey / pubkey
    privkey, pubkey = None, None
    # check if userid already exists in SQL (for this ledger)
    # this assumes that it is impossible to have user in SQL but not in Iroha...
    if userid in get_user_data(conn)['LedgerUserID']:
        warnings.warn('User already exists - nothing to add')
        return
    # check if userid already exists in Iroha (but not SQL yet)
    if get_iroha_user_info(userid).account_response.account.account_id != userid:
        # we need to create a new account entirely
        privkey = IrohaCrypto.private_key()
        pubkey = IrohaCrypto.derive_public_key(privkey)
        status = create_iroha_user_account(userid, pubkey)
        # check status for correctness, throw if bad status
        if status[0][0] == 'STATELESS_VALIDATION_FAILED':
            warnings.warn('User create transaction failed - check tx format')
            return
        if status[0][0] == 'COMMITTED':
            print('Successfully created user {} in Iroha'.format(userid))
    # once we know that the account exists in Iroha, add it to SQL as well
    ledgerid = get_ledgerids(conn, lname='Iroha')
    if privkey is None:
        privkey = ''
    else:
        privkey = str(privkey)[2:-1] # string representation of hex bytes
    if pubkey is None:
        pubkey = ''
    else:
        pubkey = str(pubkey)[2:-1] # string representation of hex bytes
    user_info = (guid, ledgerid, userid, privkey, pubkey)
    sql_qry = 'INSERT INTO {} VALUES (?,?,?,?,?)'.format(tb_name)
    c = conn.cursor()
    c.execute(sql_qry, user_info)
    conn.commit()
    print('Added user information for userid {} to SQL'.format(userid))

def create_asset(asset=LEDGER_ASSET, precision=2):
    '''
    Creates a new asset if it does not yet exist.
    '''
    # build the GetAssetInfo query
    qry = iroha.query('GetAssetInfo', asset_id=asset)
    IrohaCrypto.sign_query(qry, admin_private_key)
    status = net.send_query(qry)
    if len(status.error_response.message) != 0: # probably not the safest check
        # create the asset
        ast = asset.split('#')
        cmd = [iroha.command('CreateAsset', asset_name=ast[0], domain_id=ast[1],
                              precision=precision)]
        tx = iroha.transaction(cmd)
        IrohaCrypto.sign_transaction(tx, admin_private_key)
        net.send_tx(tx)
        return [s for s in net.tx_status_stream(tx)]
    else:
        print('Asset {} already exists'.format(asset))
        return [['ASSET_ALREADY_EXISTS']] # format hack for response parsing

def get_txid_string(tx):
    '''
    Gets a string representing the hex digest of an Iroha transaction payload.
    '''
    if not hasattr(tx, 'payload'):
        warnings.warn('No payload to hash for txid')
        return
    o = tx.payload
    b = o.SerializeToString()
    h = hashlib.sha3_256(b)
    return h.hexdigest()

def get_txid_bytes(txid):
    '''
    Gets the byte representation of a string txid needed for querying Iroha.
    '''
    return binascii.hexlify(binascii.a2b_hex(txid))

def get_tx_info(txid):
    '''
    Gets transaction info from Iroha for a transaction ID hash.
    '''
    qry = iroha.query('GetTransactions', tx_hashes=[get_txid_bytes(txid)])
    IrohaCrypto.sign_query(qry, admin_private_key)
    status = net.send_query()
    return status

# should be reconfigured to handle domains in a more robust implementation
def mint_to_account(amt, dest_acct, conn, gtxid=None, asset=LEDGER_ASSET,
                    tx_tb=dbcfg['TRANSACTION_TABLE_NAME'],
                    bal_tb=dbcfg['BALANCE_TABLE_NAME']):
    '''
    Create amt of asset on admin@test account and transfer to dest_acct.
    '''
    # attempt to create asset if it does not exist
    asset_status = create_asset(asset)
    if asset_status[0][0] not in ('COMMITTED', 'ASSET_ALREADY_EXISTS'):
        warnings.warn('Something went wrong with asset creation - check Iroha')
        return
    # make sure that dest_acct exists
    acct_status = get_iroha_user_info(dest_acct)
    if len(acct_status.error_response.message) != 0:
        warnings.warn('dest_acct does not exist - aborting mint operation')
        return
    # if asset exists, mint amt to admin and transfer to dest_acct
    sa = str(amt)
    cmd = [iroha.command('AddAssetQuantity', asset_id=asset, amount=sa),
           iroha.command('TransferAsset', src_account_id='admin@test',
                         dest_account_id=dest_acct, asset_id=asset,
                         description='Minting of asset to account', amount=sa)]
    tx = iroha.transaction(cmd)
    IrohaCrypto.sign_transaction(tx, admin_private_key)
    net.send_tx(tx)
    tx_status = [s for s in net.tx_status_stream(tx)]
    if not 'COMMITTED' in [s[0] for s in tx_status]:
        warnings.warn('Unable to commit minting transaction - check Iroha')
        return
    # if the transaction committed in Iroha, update SQLite3 database as well
    guid = get_global_userid(conn, dest_acct)
    lid = get_ledgerids(conn, lname='Iroha')
    bal = get_user_balance(conn, dest_acct)
    ts = tx.payload.reduced_payload.created_time
    txid = get_txid_string(tx)
    tx_vals = (gtxid, lid, txid, 'MINT', dest_acct, amt, ts) # pack these into tuple
    # bal_vals = (guid, lid, bal+amt)
    tx_qry = 'INSERT INTO {} VALUES (?,?,?,?,?,?,?)'.format(tx_tb)
    # insert values into SQL store
    c = conn.cursor()
    c.execute(tx_qry, tx_vals)
    conn.commit()
    update_balance(conn, guid, lid, bal+amt, bal_tb)
    print('Added transaction info for minting transaction {}'.format(txid))

def transfer_asset(from_acct, to_acct, amt, conn, memo=None, gtxid=None,
                   asset=LEDGER_ASSET, tx_tb=dbcfg['TRANSACTION_TABLE_NAME'],
                   bal_tb=dbcfg['BALANCE_TABLE_NAME']):
    '''
    Transfer amt of asset from one account to another.
    '''
    # check for valid amt and memo params
    assert amt > 0, 'amt must be a positive numeric value'
    amt = round(amt, 2)
    if memo is not None:
        assert type(memo) == str, 'memo must be in string format'
    else:
        memo = ''
    # check that from acct has at least amt of asset available
    from_bal = get_user_balance(conn, from_acct, bal_tb)
    if from_bal < amt:
        warnings.warn('Account {} has insufficient funds'.format(from_acct))
        return
    # if from_acct has sufficient balance, prepare the transaction in Iroha
    sa = str(amt)
    lid = get_ledgerids(conn, lname='Iroha')
    cmd = [iroha.command('TransferAsset', src_account_id=from_acct, \
                         dest_account_id=to_acct, asset_id=asset, \
                         description=memo, amount=sa)]
    # create the transaction *as* from_acct
    tx = Iroha(from_acct).transaction(cmd)
    from_privkey = get_privkey(conn, from_acct, lid)
    IrohaCrypto.sign_transaction(tx, from_privkey)
    net.send_tx(tx)
    tx_status = [s for s in net.tx_status_stream(tx)]
    if not 'COMMITTED' in [s[0] for s in tx_status]:
        warnings.warn('Unable to commit transfer transaction - check Iroha')
        return
    # if the transaction is committed in Iroha, add to SQL tables as well
    guid_from = get_global_userid(conn, from_acct)
    guid_to = get_global_userid(conn, to_acct)
    lid = get_ledgerids(conn, lname='Iroha')
    bal_from = get_user_balance(conn, from_acct)
    bal_to = get_user_balance(conn, to_acct)
    ts = tx.payload.reduced_payload.created_time
    txid = get_txid_string(tx)
    tx_vals = (gtxid, lid, txid, from_acct, to_acct, amt, ts) # pack these into tuple
    tx_qry = 'INSERT INTO {} VALUES (?,?,?,?,?,?,?)'.format(tx_tb)
    # insert values into SQL store
    c = conn.cursor()
    c.execute(tx_qry, tx_vals)
    conn.commit()
    update_balance(conn, guid_from, lid, bal_from-amt, bal_tb)
    update_balance(conn, guid_to, lid, bal_to+amt, bal_tb)
    print('Added transaction info for transfer {}'.format(txid))
