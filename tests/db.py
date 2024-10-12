from libStreamDetective.db import *
import unittest

class TestCooldowns(unittest.TestCase):
    def test_memory_db(self):
        self.dbchecks(':memory:')

    def test_disk_db(self):
        self.dbchecks('sddb.sqlite3')

    def dbchecks(self, dbname):
        close()
        connect(dbname)
        tables = fetchall("SELECT * FROM sqlite_master")
        self.assertTrue(tables, 'got tables')
        for r in tables:
            print(r)

        self.assertTrue(tableExists('gAmEs'), 'games exists')
        self.assertFalse(tableExists('boringstuff'), 'boring things do not exist here')

    def test_insert(self):
        close()
        connect(':memory:')

        insert('games', dict(name='Deus Ex', id='0451', updated=1))
        res = fetchall('select updated from games where name=?', ('Deus Ex',))
        self.assertEqual(len(res), 1, 'found 1 game')
        self.assertEqual(res[0][0], 1, 'updated==1')
        with self.assertRaises(sqlite3.IntegrityError):
            insert('games', dict(name='Deus Ex', id='0451', updated=1))


    def test_upsert(self):
        close()
        connect(':memory:')

        upsert('games', dict(name='Deus Ex', id='0451', updated=1))
        res = fetchall('select updated from games where name=?', ('Deus Ex',))
        self.assertEqual(len(res), 1, 'found 1 game')
        self.assertEqual(res[0][0], 1, 'updated==1')

        upsert('games', dict(name='Deus Ex', id='0451', updated=2))
        res = fetchall('select updated from games where name=?', ('Deus Ex',))
        self.assertEqual(len(res), 1, 'found 1 game')
        self.assertEqual(res[0][0], 2, 'updated==2')

        upsert('games', dict(name='The 7th Guest', id='1993', updated=3))
        res = fetchall('select updated from games where name=?', ('The 7th Guest',))
        self.assertEqual(len(res), 1, 'found 1 game')
        self.assertEqual(res[0][0], 3, 'updated==3')

        res = fetchall('select name from games')
        self.assertEqual(len(res), 2, 'found 2 games')
