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

        self.assertTrue(tableExists('games'), 'games exists')
        self.assertFalse(tableExists('boringstuff'), 'boring things do not exist here')
        close()
