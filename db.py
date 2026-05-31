import pymysql
from pymysql.cursors import DictCursor
from dbutils.pooled_db import PooledDB

DB_CONFIG = {
    'host': 'localhost',
    'user': 'thuchi_admin',
    'password': '123',
    'database': 'thu_chi_db',
    'charset': 'utf8mb4',
    'cursorclass': DictCursor
}

pool = PooledDB(
    creator=pymysql,
    mincached=2,
    maxcached=5,
    maxconnections=10,
    blocking=True,
    **DB_CONFIG
)

def get_connection():
    return pool.connection()