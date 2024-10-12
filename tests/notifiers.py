import unittest
from libStreamDetective import db, notifiers
from libStreamDetective.util import unixtime

class TestNotifiers(unittest.TestCase):
    def test_TimeMult(self):
        notifierData = {'minTime':43200, 'maxTime':86400}
        mult = notifiers.GetTimeMult('test1', 'search1', notifierData)
        self.assertEqual(mult, 1)
        
        db.upsert('notifiers_searches', dict(notifier='test1', search_id='search1', last=unixtime()))
        mult = notifiers.GetTimeMult('test1', 'search1', notifierData)
        self.assertEqual(mult, 0)

        db.upsert('notifiers_searches', dict(notifier='test1', search_id='search1', last=unixtime()-43200))
        mult = notifiers.GetTimeMult('test1', 'search1', notifierData)
        self.assertAlmostEqual(mult, 0)

        db.upsert('notifiers_searches', dict(notifier='test1', search_id='search1', last=unixtime()-64800))
        mult = notifiers.GetTimeMult('test1', 'search1', notifierData)
        self.assertAlmostEqual(mult, 0.5)

        db.upsert('notifiers_searches', dict(notifier='test1', search_id='search1', last=unixtime()-86400))
        mult = notifiers.GetTimeMult('test1', 'search1', notifierData)
        self.assertAlmostEqual(mult, 1)

        db.upsert('notifiers_searches', dict(notifier='test1', search_id='search1', last=unixtime()-96400))
        mult = notifiers.GetTimeMult('test1', 'search1', notifierData)
        self.assertEqual(mult, 1)
