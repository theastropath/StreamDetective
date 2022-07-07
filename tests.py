from libStreamDetective.libStreamDetective import *
import unittest

class TestStreamDetective(StreamDetective):
    def __init__(self, tester):
        self.tester = tester
        StreamDetective.__init__(self)

    def HandleConfigFile(self):
        print("Reading default config.json file")
        exampleConfigFileFullPath = os.path.join(path,"config.example.json")
        with open(exampleConfigFileFullPath, 'r') as f:
            self.config = json.load(f)
        
        self.config['clientId'] = '123456789012345678901234567890'
        self.config['accessToken'] = '123456789012345678901234567890'

        self.config['DiscordProfiles'][0]['Webhook'] = '1234567890'

        self.config['TwitterAccounts'][0] = {
            "AccountName": "TwitterTest",
            "ApiKey":"1234567890123456789012345",
            "ApiKeySecret":"12345678901234567890123456789012345678901234567890",
            "AccessToken":"1234567890123456789-123456789012345678901234567890",
            "AccessTokenSecret":"123456789012345678901234567890123456789012345",
            "BearerToken":"123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901"
        }
        self.TestConfig()
    
    def TwitchApiRequest(self, url, headers):
        if self.gameIdUrlBase in url:
            return {'data': [{'id': 'foobar'}]}
        elif self.streamsUrl in url:
            return {'data': []}
        return {}
    
    def SaveCacheFiles(self):
        return
    
    def LoadCacheFiles(self):
        self.gameIdCache = {}
        self.tagsCache = {}
        self.cooldowns = {}

    def ReadGameCache(self, game):
        return {}

    def WriteGameCache(self, game, streamInfo):
        return

    def sendTweet(self,profile,msg):
        return
    
    def sendWebhookMsg(self, discordProfile, content, embeds, atUserId):
        return



class BaseTestCase(unittest.TestCase):
    def test_example(self):
        sd = TestStreamDetective(self)
        self.assertEqual(1, 1)

unittest.main(verbosity=9, warnings="error")#, failfast=True)
