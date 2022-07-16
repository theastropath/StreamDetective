from typeguard import typechecked, importhook
importhook.install_import_hook('libStreamDetective')
from libStreamDetective.libStreamDetective import *
import unittest

failures = []

class BetterAssertionError(AssertionError):
    def __init__(self, *args):
        global failures
        AssertionError.__init__(self, *args)
        failures.append(self)
        logex(self)

@typechecked
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

@typechecked
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
            
    def HandleStreamers(self):# same thing as normal, but without the try/except
        for streamer in self.config["Streamers"]:
            self.HandleStreamer(streamer)

    def HandleSearches(self):# same thing as normal, but without the try/except
        for search in self.config.get("Searches",[]):
            if "GameName" in search:
                self.HandleGame(search)
            elif "UserName" in search:
                self.HandleStreamer(search)

    def HandleGame(self, game: dict):
        self.tweetsSent = 0
        self.webhooksSent = 0
        self.pushbulletsSent = 0
        self.cooldownsCaught = 0
        newStreams = super().HandleGame(game)
        self.tester.assertEqual(len(newStreams), 1, 'newStreams')

        if "defaultTwitter" in game.get('Notifications',[]):
            self.tester.assertEqual(self.tweetsSent, 1, 'tweetsSent')
        else:
            self.tester.assertEqual(self.tweetsSent, 0, 'no tweetsSent')
        
        if "defaultDiscord" in game.get('Notifications',[]):
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

    def GetAllGameStreams(self,gameId:str):
        return self.fetchedGames.get(str(123),[]) #TwitchApiRequest always returns game id 123

    def GetAllStreamerStreams(self,streamer) -> list:
        return super().GetAllStreamerStreams("userlogin") #TwitchApiRequest always returns userlogin

    def HandleStreamer(self, streamer):
        self.tweetsSent = 0
        self.webhooksSent = 0
        self.pushbulletsSent = 0
        self.cooldownsCaught = 0

        newStreams = super().HandleStreamer(streamer)
        
        self.tester.assertEqual(len(newStreams), 1, 'newStreams')

        if "defaultTwitter" in streamer.get('Notifications',[]):
            if self.cooldownsCaught:
                self.tester.assertGreaterEqual(self.cooldownsCaught, 1, 'cooldownsCaught')
            else:
                self.tester.assertEqual(self.tweetsSent, 1, 'tweetsSent')
        else:
            self.tester.assertEqual(self.tweetsSent, 0, 'no tweetsSent')
        
        if "defaultDiscord" in streamer.get('Notifications',[]):
            if self.cooldownsCaught:
                self.tester.assertGreaterEqual(self.cooldownsCaught, 1, 'cooldownsCaught')
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

        self.config['NotificationServices'][0]['Webhook'] = '1234567890'

        self.config['NotificationServices'][1] = {
            "ProfileName": "defaultTwitter",
            "Type":"Twitter",
            "ApiKey":"1234567890123456789012345",
            "ApiKeySecret":"12345678901234567890123456789012345678901234567890",
            "AccessToken":"1234567890123456789-123456789012345678901234567890",
            "AccessTokenSecret":"123456789012345678901234567890123456789012345",
            "BearerToken":"123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901"
        }
        
        self.config['NotificationServices'][2]['ApiKey'] = '1234567890'

        self.TestConfig()
    
    def TwitchApiRequest(self, url, headers={}):
        self.tester.assertEqual(type(headers), dict)
        if self.gameIdUrlBase in url:
            return {'data': [{'id': 'foobar','box_art_url':'videogames'}]}
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
        self.gameArtCache = {}
        self.tagsCache = {}
        self.cooldowns = {}

    def ReadGameCache(self, game):
        return {}

    def WriteGameCache(self, game, streamInfo):
        return
        
    def ReadStreamerCache(self, streamer):
        return {}

    def WriteStreamerCache(self, streamer, streamInfo):
        return

    def checkIsOnCooldown(self, stream, webhookUrl):
        if super().checkIsOnCooldown(stream, webhookUrl):
            self.cooldownsCaught+=1
            return True
        return False

    def sendTweet(self,profile,msg):
        self.tweetsSent += 1
    
    def sendWebhookMsg(self, discordProfile, content, embeds, atUserId, avatarUrl):
        self.webhooksSent += 1
        
    def sendPushBulletMessage(self,apiKey,title,body,emails=None,url=None):
        self.pushbulletsSent += 1


setVerbose(9)
unittest.main(verbosity=9, warnings="error")#, failfast=True)
