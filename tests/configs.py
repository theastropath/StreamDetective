import os
import unittest
from libStreamDetective import libStreamDetective
from tests import TestStreamDetectiveBase

class TestConfigs(unittest.TestCase):
    def test_example_configs(self):
        sd = TestStreamDetectiveBase()

    def test_real_configs(self):
        sd = TestStreamDetectiveConfig()

class TestStreamDetectiveConfig(libStreamDetective.StreamDetective):
    def __init__(self):
        path = libStreamDetective.path
        configFileFullPath = os.path.join(path, self.configFileName)
        searchesPath = os.path.join(path, self.searchesFolderPath)
        self.notifiers = {}

        if not os.path.exists(configFileFullPath):
            print('no config.json file, skipping test')
        elif not os.path.exists(searchesPath):
            print('no searches folder, skipping test')
        else:
            self.HandleConfigFile()

