'''
Shared API should have following functions:

- Create a new user
    - should create a GLOBAL UID as well as call the individual ledger APIs to
      create local user IDs there
    - this can create the entry in the Users table; individual APIs only need
      to interact with Ledger Users table
- Mint to account
    - should create local DLT tokens (via individual ledger APIs) at the local
      account corresponding to a single global account
- Transfer from X to Y
    - should send tokens from account X to account Y on each individual ledger
'''

# imports
import yaml
import sqlite3
import pandas as pd
import warnings
from db_functions import *
import api_iroha as irh
import api_elements as elt

# configuration
dbcfg = yaml.load(open('../config/db_config.yaml'), Loader=yaml.SafeLoader)
dltcfg = yaml.load(open('dltcfg.yaml'), Loader=yaml.SafeLoader)
conn = sqlite3.connect('../config/{}'.format(dbcfg['DB_NAME']))

# functions
def create_account(username, conn, tb_name=dbcfg['USER_TABLE_NAME']):
    '''
    This should first create a new global user entry in the Users table, then pass the (now known) guid to the various per-ledger APIs to add their own entries to the Ledger User tables.
    '''
    # validate new username
    assert type(username) == str, 'username must be a string'
    if username in get_platform_users(conn):
        warnings.warn('User {} already exists!'.format(username))
        return
    # create new platform-level user entry
    guid = get_max_userid(conn) + 1
    user_info = (guid, username)
    sql_qry = 'INSERT INTO {} VALUES (?,?)'.format(tb_name)
    c = conn.cursor()
    c.execute(sql_qry, user_info)
    conn.commit()
    print('Added new platform user {} to SQL'.format(username))
    # once the user is in the global platform, add to various DLT platforms
    iroha_uid = '{}@{}'.format(username, dltcfg['IROHA_DOMAIN'])
    irh.add_user_to_db(iroha_uid, guid, conn)
    elt.add_user_to_db(username, guid, conn)
    
    # add other DLT API calls here when ready

    print('Finished creating DLT user accounts for user {}'.format(username))

def mint_to_account():
    '''
    This should first update ledger / balance entries for the "base ledger" (need to add this to ledger master data...)
    Once it has done so, it should call the other ledgers to mint. These functions should return a status code which is SHARED ACROSS THE WHOLE SYSTEM -- add to cfg.
    WITHIN THE LEDGER-SPECIFIC FUNCTION, the SQL database should ONLY be updated if the transaction successfully confirmed on the blockchain ledger.
    Failure status codes can notify this function that the ledgers will now be out of sync; can handle that here in some fashion.

    **N.B. In general, the above pattern should be used where sensible: update the relevant parts of the SQL DB for the "base ledger" right away; call the other DLT ledgers, and during internal execution of those, FIRST try the transaction on that DLT ledger, and if successful, update the relevant SQL table(s) with the DLT-specific transaction / balance data.
    '''
    return
