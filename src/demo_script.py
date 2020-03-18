# script to rebuild database and add some test users / transactions

# import other scripts
import sys
sys.path.append('../')
from config.db_setup import *
from api_iroha import *

# config
cfg = yaml.load(open('../config/db_config.yaml'), Loader=yaml.SafeLoader)
conn = sqlite3.connect('../config/{}'.format(cfg['DB_NAME']))

# rebuild a fresh version of the database
full_rebuild(conn)

# create 2 new users in Iroha
add_user_to_db('alice@test', conn)
add_user_to_db('bob@test', conn)

# grant users some initial funds
mint_to_account(50, 'alice@test', gtxid=1, conn=conn)
mint_to_account(15, 'bob@test', gtxid=2, conn=conn)

# transfer from one user to another
transfer_asset('alice@test', 'bob@test', 5.5, conn, 'test transfer of 5.5')

# see if it worked
print(get_balances())
