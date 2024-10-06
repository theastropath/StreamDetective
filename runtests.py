import autoinstaller
import unittest
from pathlib import Path

if __name__ == '__main__':
    root = Path(__file__).parent
    suite = unittest.defaultTestLoader.discover(root/'tests', '*.py', root)
    testrunner = unittest.TextTestRunner(buffer=True, failfast=True, warnings='error', verbosity=9)
    testrunner.run(suite)
