import os

import kirari.db as db
from kirari.constants import *

base_id = os.environ['BASE_ID']
base_name = os.environ['BASE_NAME']
base_cf = os.environ['BASE_CF']

os.system("rm -rf ./resources/db.sqlite")
# db.common_write("admin_list", [])

db.db_write(mbrc_id, "name", base_name)
db.db_write(mbrc_id, "cf_id", base_cf)
db.db_write(mbrc_id, "cf_score", 0)
db.db_write(mbrc_id, "kirari_score", 0)

db.common_write("admin_list", [base_id])
db.common_write("user_list", [base_id])
db.db_write(server_uid, "score", 0)

db.common_write("game_on", False)
db.common_write("game_begin_time", 0)
db.common_write("betting_on", False)
