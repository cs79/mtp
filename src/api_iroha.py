# API adapter for Iroha allowing generic functionality called by api_shared

# imports
import sqlite3
from db_functions import * # own script
import pandas as pd
from iroha import Iroha, IrohaGrpc, IrohaCrypto
from iroha.primitive_pb2 import can_set_my_account_detail
import warnings, re

# configuration (per Iroha example guide for now)
admin_private_key = 'f101537e319568c765b2cc89698325604991dca57b9716b58016b253506cab70'
user_private_key = IrohaCrypto.private_key()
user_public_key = IrohaCrypto.derive_public_key(user_private_key)
iroha = Iroha('admin@test')
net = IrohaGrpc()

DB_NAME = 'mtp.db'
conn = sqlite3.connect(DB_NAME)

UID_PAT = '[a-z0-9]+@[a-z0-9]+'

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
def add_user_to_db(userid, conn=conn, tb_name=cfg['LEDGER_USER_TABLE_NAME']):
    '''
    Add a user to the Iroha ledger and the shared database.
    N.B. userid should be in proper Iroha format, e.g. "user@domain".
    '''
    # check correct userid format
    assert re.match(UID_PAT, userid) is not None, 'invalid userid format'
    # empty placeholders for privkey / pubkey
    privkey, pubkey = None, None
    # check if userid already exists in SQL (for this ledger)
    if userid in get_user_data()['LedgerUserID']:
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
    global_uid = get_max_userid() + 1
    ledgerid = int(get_ledgerids(lname='Iroha')['LedgerID'][0])
    if privkey is None:
        privkey = ''
    else:
        privkey = str(privkey)[2:-1] # string representation of hex bytes
    if pubkey is None:
        pubkey = ''
    else:
        pubkey = str(pubkey)[2:-1] # string representation of hex bytes
    user_info = (global_uid, ledgerid, userid, privkey, pubkey)
    sql_qry = 'INSERT INTO {} VALUES (?,?,?,?,?)'.format(tb_name)
    c = conn.cursor()
    c.execute(sql_qry, user_info)
    conn.commit()
    print('Added user information for userid {} to SQL'.format(userid))
