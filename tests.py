from libStreamDetective.libStreamDetective import *
import unittest

failures = []

class BetterAssertionError(AssertionError):
    def __init__(self, *args):
        global failures
        AssertionError.__init__(self, *args)
        failures.append(self)
        logex(self)


class BaseTestCase(unittest.TestCase):
    def __init__(self, *args):
        unittest.TestCase.__init__(self, *args)
        self.failureException = BetterAssertionError

    def setUp(self):
        global failures
        failures = []
        super().setUp()
    
    def tearDown(self):
        global failures
        numDetectedErrors = 0
        for error in self._outcome.errors:
            if error[1]:
                numDetectedErrors+=1
        if numDetectedErrors==0:
            for fail in failures:
                logex(fail, 'caught failure')
            self.assertEqual(len(failures), 0, 'caught exceptions')
        
        return super().tearDown()

    def test_example(self):
        sd = TestStreamDetective(self)


class TestStreamDetective(StreamDetective):
    def __init__(self, tester: BaseTestCase):
        self.tester = tester
        self.totalTweetsSent = 0
        self.totalWebhooksSent = 0
        self.totalPushbulletsSent = 0
        self.totalCooldownsCaught = 0
        StreamDetective.__init__(self)
        self.tester.assertGreaterEqual(self.totalTweetsSent, 1, 'totalTweetsSent')
        self.tester.assertGreaterEqual(self.totalWebhooksSent, 1, 'totalWebhooksSent')
        self.tester.assertGreaterEqual(self.totalPushbulletsSent, 1, 'totalPushbulletsSent')
        self.tester.assertGreaterEqual(self.totalCooldownsCaught, 1, 'totalCooldownsCaught')

    def HandleGames(self):# same thing as normal, but without the try/except
        for game in self.config["Games"]:
            self.HandleGame(game)

    def HandleGame(self, game):
        self.tweetsSent = 0
        self.webhooksSent = 0
        self.pushbulletsSent = 0
        self.cooldownsCaught = 0
        newStreams = super().HandleGame(game)
        self.tester.assertEqual(len(newStreams), 1, 'newStreams')

        if game.get('Twitter') or game.get('Notifications'):
            self.tester.assertEqual(self.tweetsSent, 1, 'tweetsSent')
        else:
            self.tester.assertEqual(self.tweetsSent, 0, 'no tweetsSent')
        
        if game.get('DiscordProfile') or game.get('Notifications'):
            if self.cooldownsCaught:
                self.tester.assertEqual(self.cooldownsCaught, 1, 'cooldownsCaught')
            else:
                self.tester.assertEqual(self.webhooksSent, 1, 'webhooksSent')
        else:
            self.tester.assertEqual(self.webhooksSent, 0, 'no webhooksSent')
        
        self.totalTweetsSent += self.tweetsSent
        self.totalWebhooksSent += self.webhooksSent
        self.totalCooldownsCaught += self.cooldownsCaught
        self.totalPushbulletsSent += self.pushbulletsSent

    def HandleConfigFile(self):
        print("Reading default config.json file")
        exampleConfigFileFullPath = os.path.join(path,"config.example.json")
        with open(exampleConfigFileFullPath, 'r') as f:
            self.config = json.load(f)
        
        with self.tester.assertRaises(Exception):
            self.TestConfig()

        self.config['clientId'] = '123456789012345678901234567890'
        self.config['accessToken'] = '123456789012345678901234567890'

        self.config['DiscordProfiles'][0]['Webhook'] = '1234567890'

        self.config['TwitterAccounts'][0] = {
            "AccountName": "default",
            "ApiKey":"1234567890123456789012345",
            "ApiKeySecret":"12345678901234567890123456789012345678901234567890",
            "AccessToken":"1234567890123456789-123456789012345678901234567890",
            "AccessTokenSecret":"123456789012345678901234567890123456789012345",
            "BearerToken":"123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901"
        }

        self.config['NotificationServices'][0] = {
            "ProfileName": "TestProfile1",
            "Type":"Discord",
            "Webhook":"1234567890",
			"UserName":"0987654321"
        }

        self.config['NotificationServices'][1] = {
            "ProfileName": "TestProfile2",
            "Type":"Twitter",
            "ApiKey":"1234567890123456789012345",
            "ApiKeySecret":"12345678901234567890123456789012345678901234567890",
            "AccessToken":"1234567890123456789-123456789012345678901234567890",
            "AccessTokenSecret":"123456789012345678901234567890123456789012345",
            "BearerToken":"123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901"
        }
		
        self.config['NotificationServices'][2] = {
            "ProfileName": "TestProfile3",
            "Type":"Pushbullet",
            "ApiKey":"1234567890123456789012345",
        }
        
        self.config['Games'].append({})
        self.config['Games'][-1]= {
            "GameName":"LasagnaEaterPro",
            "Notifications":["TestProfile1","TestProfile2","TestProfile3"]
        }

        self.TestConfig()
    
    def TwitchApiRequest(self, url, headers={}):
        self.tester.assertEqual(type(headers), dict)
        if self.gameIdUrlBase in url:
            return {'data': [{'id': 'foobar'}]}
        elif self.streamsUrl in url:
            return {'data': [
                {
                    "id": "123",
                    "user_id": "123",
                    "user_login": "userlogin",
                    "user_name": "username",
                    "game_id": "123",
                    "game_name": "Deus Ex",
                    "type": "live",
                    "title": "Deus Ex Randomizer",
                    "viewer_count": 2052,
                    "started_at": "2020-06-22T00:00:00Z",
                    "language": "en",
                    "thumbnail_url": "https://static-cdn.jtvnw.net/previews-ttv/live_user_userlogin-{width}x{height}.jpg",
                    "tag_ids": ["2fd30cb8-f2e5-415d-9d42-1316cfa61367"],
                    "is_mature": True,
                    "last_seen": "2020-06-22T00:00:00Z"
                }
            ]}
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

    def checkIsOnCooldown(self, stream, webhookUrl):
        if super().checkIsOnCooldown(stream, webhookUrl):
            self.cooldownsCaught+=1
            return True
        return False

    def sendTweet(self,profile,msg):
        self.tweetsSent += 1
    
    def sendWebhookMsg(self, discordProfile, content, embeds, atUserId):
        self.webhooksSent += 1
        
    def sendPushBulletMessage(self,apiKey,title,body,emails=None,url=None):
        self.pushbulletsSent += 1


setVerbose(9)
unittest.main(verbosity=9, warnings="error")#, failfast=True)
