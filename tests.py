from libStreamDetective.libStreamDetective import *
import unittest

class BaseTestCase(unittest.TestCase):
    def test_example(self):
        self.assertEqual(1, 1)

unittest.main(verbosity=9, warnings="error")#, failfast=True)
