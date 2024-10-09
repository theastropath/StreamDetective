import sqlite3
from contextlib import contextmanager, closing

con = None

def connect(dbname: str):
    global con
    if con:
        return
    
    con = sqlite3.connect(dbname)
    # TODO: check DB version, create tables...

    exec('create table if not exists sd_meta (version integer)')
    existing_version = fetchone('select version from sd_meta')
    if existing_version:
        existing_version = existing_version[0]
    else:
        existing_version = 0
    current_version = 1 # we don't need to bump the version if we just add a new table
    if existing_version < current_version:
        exec('delete from sd_meta')
        exec('insert into sd_meta values (?)', (current_version,))
        upgrade(existing_version, current_version)
    elif current_version < existing_version:
        raise NotImplementedError('database is newer than code!', existing_version, current_version)
    
    # create if not exists all tables
    exec('create table if not exists games (name text PRIMARY KEY, id text, updated integer)')
    exec('create table if not exists cooldowns (streamer text, notifier text, last integer, PRIMARY KEY(streamer, notifier))')
    exec('create table if not exists streams (id text, streamer text PRIMARY KEY, title text, game text, tags text, updated integer, language text)')
    exec('create table if not exists queries (baseurl text, cursor text, page integer)')
    # a table for lotteries? how many times each game/streamer has won?
    # a table for tags? how many times they have been featured in different games or by different streamers?
    # cleanup old rows?


def upgrade(existing_version, current_version):
    print('upgrading db from:', existing_version, 'to:', current_version)
    # drop tansient tables
    exec('drop table if exists games')
    exec('drop table if exists queries')
    # TODO: do some if statements for specific upgrades based on version numbers
    if existing_version < 100:
        exec('drop table if exists cooldowns')
        exec('drop table if exists streams')
        return


def close():
    global con
    if con:
        con.commit()
        con.close()
        con = None

@contextmanager
def cursor():
    global con
    cur = con.cursor()
    try:
        yield cur
    finally:
        con.commit()
        cur.close()

def fetchone(sql: str, params=()):
    with cursor() as c:
        c.execute(sql, params)
        return c.fetchone()
    
def fetchall(sql: str, params=()):
    with cursor() as c:
        c.execute(sql, params)
        return c.fetchall()
    
def exec(sql: str, params=()):
    with cursor() as c:
        c.execute(sql, params)
        return c.lastrowid

def execmany(sql: str, params=()):
    with cursor() as c:
        c.executemany(sql, params)
        return c.lastrowid

def tableExists(table):
    # table names are case-insensitive in SQLite, but values are case-sensistive
    return bool(fetchone("SELECT name FROM sqlite_master WHERE type='table' AND name=? COLLATE NOCASE", (table,)))
