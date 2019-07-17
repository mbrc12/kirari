import logging
import sys
from sqlitedict import SqliteDict
import json
import urllib.request

from kirari.constants import db_path, json_path, common_uid

sep = '$'
logger = logging.getLogger(__name__)


def open_db():
    try:
        return SqliteDict(db_path, autocommit=True)
    except Exception:
        logger.error("Could not open database")
        sys.exit()


def db_read(user, property):
    db = open_db()

    try:
        return db[str(user) + sep + str(property)]
    except Exception:
        logger.error("Could not find %s.%s in database" % (user, property))
        sys.exit()

    try:
        db.close()
    except Exception:
        logger.error("Could not properly close database")
        sys.exit()


def db_write(user, property, value):
    db = open_db()

    try:
        db[str(user) + sep + str(property)] = value
    except Exception:
        logger.error("Could not write %s.%s = %s in database" %
                     (user, property, value))
        sys.exit()

    try:
        db.close()
    except Exception:
        logger.error("Could not properly close database")
        sys.exit()


def common_read(property):
    return db_read(common_uid, property)


def common_write(property, value):
    return db_write(common_uid, property, value)

def put_json():
    db = open_db()
    dict_db = dict(db)
    fp = open(json_path, 'w')
    json.dump(dict_db, fp)
    db.close()

def get_json(url):
    ext_db = {}
    try: 
        data = urllib.request.urlopen(url).read()
        ext_db = json.loads(data)
    except Exception:
        return False
    
    db = open_db()

    all_keys = db.keys()
    for key in all_keys:
        db.pop(key, None)

    for key in ext_db:
        db[key] = ext_db[key]

    db.close()

    return True



