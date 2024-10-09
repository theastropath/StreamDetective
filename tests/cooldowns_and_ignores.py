
import unittest
from tests import TestStreamDetectiveBase

class TestCooldowns(unittest.TestCase):
    def test_cooldowns(self):
        stream = {'user_login':'Die4Ever'}
        sd1 = TestStreamDetectiveBase()
        ret = sd1.checkIsOnCooldown(stream, 'discord.com')
        self.assertFalse(ret, 'not on cooldown first time')
        ret = sd1.checkIsOnCooldown(stream, 'discord.com')
        self.assertTrue(ret, 'on cooldown second time')
        ret = sd1.checkIsOnCooldown(stream, 'mastodon.social')
        self.assertFalse(ret, 'not on cooldown for mastodon')

        sd2 = TestStreamDetectiveBase(clearCache=False)
        ret = sd2.checkIsOnCooldown(stream, 'discord.com')
        self.assertTrue(ret, 'still on cooldown after reload')

        sd2.config['CooldownSeconds'] = -10
        ret = sd2.checkIsOnCooldown(stream, 'discord.com')
        self.assertFalse(ret, 'no longer on cooldown with negative timeout')


    def test_ignores(self):
        stream = {'user_login': 'Die4Ever'}
        streams = [stream]
        sd1 = TestStreamDetectiveBase()
        ret = sd1.filterIgnoredStreams('Discord', streams)
        self.assertEqual(len(ret), 1, 'not ignored first time')
        ret = sd1.filterIgnoredStreams('Discord', streams)
        self.assertEqual(len(ret), 0, 'ignored second time')
        ret = sd1.filterIgnoredStreams('Mastodon', streams)
        self.assertEqual(len(ret), 1, 'not ignored for mastodon')

        sd2 = TestStreamDetectiveBase(clearCache=False)
        ret = sd2.filterIgnoredStreams('Discord', streams)
        self.assertEqual(len(ret), 0, 'still ignored after reload')

        sd2.config['CooldownSeconds'] = -10
        ret = sd2.filterIgnoredStreams('Discord', streams)
        self.assertEqual(len(ret), 1, 'no longer ignored with negative timeout')

        sd2.config['IgnoreStreams'] = ['theastropath']
        ret = sd2.filterIgnoredStreams('Discord', streams)
        self.assertEqual(len(ret), 1, 'no longer ignored with negative timeout')

        sd2.config['IgnoreStreams'] = ['die4ever'] # TestConfig function normally sets this to lowercase
        ret = sd2.filterIgnoredStreams('Discord', streams)
        self.assertEqual(len(ret), 0, 'ignored via IgnoreStreams config')
