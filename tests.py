from typeguard import typechecked, importhook
importhook.install_import_hook('libStreamDetective')
from libStreamDetective.libStreamDetective import *
import shutil
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

    def verboseAssert(self, caller, testname:str, *args):
        print('')
        print(str(self._testMethodName)+'()', type(caller).__name__)
        print('|__ ' + testname +'(', end='')
        print(*args, sep=', ', end=')\n\n')
        func = getattr(self, testname)
        func(*args)

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
        sd = TestStreamDetective1(self)
    
    def test_cooldown(self):
        sd = TestCooldown(self, 0)
        sd = TestCooldown(self, 1)
        sd = TestCooldown(self, 2)

    def test_multiples(self):
        sd = TestMultiples(self)


def GetCacheDir():
    tempDir = os.path.join(tempfile.gettempdir(),"streamstests")
    return tempDir


@typechecked
class TestStreamDetectiveBase(StreamDetective):
    def __init__(self, tester: BaseTestCase, startIteration=0):
        print('\n\n', type(self), '__init__ starting')
        self.tester = tester
        self.totalTweetsSent = 0
        self.totalWebhooksSent = 0
        self.totalPushbulletsSent = 0
        self.totalCooldownsCaught = 0
        self.twitchApiCalls = 0
        self.getStreamsApiCalls = 0
        self.tempDir = GetCacheDir()
        self.iterations = startIteration
        StreamDetective.__init__(self, dry_run=False, tempDir=self.tempDir)
        print('\n', type(self), '__init__ done\n')

    def test(self, testname:str, *args):
        self.tester.verboseAssert(self, testname, *args)

    def ClearCache(self):
        print('Clearing Cache '+str(type(self)))
        self.tempDir = GetCacheDir()
        if os.path.isdir(self.tempDir):
            shutil.rmtree(self.tempDir)
        if not os.path.exists(self.tempDir):
            os.makedirs(self.tempDir)

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
        self.totalTweetsSent += self.tweetsSent
        self.totalWebhooksSent += self.webhooksSent
        self.totalCooldownsCaught += self.cooldownsCaught
        self.totalPushbulletsSent += self.pushbulletsSent
        self.iterations += 1
        return newStreams

    def GetAllGameStreams(self,gameId:str):
        return self.fetchedGames.get(gameId,[]) #TwitchApiRequest always returns game id 123

    def GetAllStreamerStreams(self,streamer) -> list:
        return super().GetAllStreamerStreams(streamer) #TwitchApiRequest always returns userlogin

    def HandleStreamer(self, streamer):
        self.tweetsSent = 0
        self.webhooksSent = 0
        self.pushbulletsSent = 0
        self.cooldownsCaught = 0
        newStreams = super().HandleStreamer(streamer)
        self.totalTweetsSent += self.tweetsSent
        self.totalWebhooksSent += self.webhooksSent
        self.totalCooldownsCaught += self.cooldownsCaught
        self.totalPushbulletsSent += self.pushbulletsSent
        return newStreams

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
    
    def GetGameId(self, gameName):
        gameId = gameName
        self.AddGameIdToCache(gameName,gameId)
        self.AddGameArtToCache(gameName,'boxArt')
        return gameId
    
    def TwitchApiRequest(self, url, headers={}):
        self.twitchApiCalls += 1
        print('mocked TwitchApiRequest', url, headers)
        self.tester.assertEqual(type(headers), dict)
        if self.streamsUrl in url and 'game_id=' in url:
            self.getStreamsApiCalls += 1
            ret = []
            if 'game_id=Deus Ex' in url:
                ret.append({
                    "id": str(1000+self.iterations),
                    "user_id": "123",
                    "user_login": "Heinki",
                    "user_name": "Heinki",
                    "game_id": "Deus Ex",
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
                })
            if 'game_id=Fall Guys' in url:
                ret.append({
                    "id": str(2000+self.iterations),
                    "user_id": "124",
                    "user_login": "thefallguy",
                    "user_name": "thefallguy",
                    "game_id": "Fall Guys",
                    "game_name": "Fall Guys",
                    "type": "live",
                    "title": "Fall Guys Randomizer",
                    "viewer_count": 2052,
                    "started_at": "2020-06-22T00:00:00Z",
                    "language": "en",
                    "thumbnail_url": "https://static-cdn.jtvnw.net/previews-ttv/live_user_userlogin-{width}x{height}.jpg",
                    "tag_ids": [],
                    "is_mature": True,
                    "last_seen": "2020-06-22T00:00:00Z"
                })
            return { 'data': ret }
        elif self.streamsUrl in url and 'user_login=YourFavouriteStreamer' in url:
            self.getStreamsApiCalls += 1
            return {'data': [
                {
                    "id": str(3000+self.iterations),
                    "user_id": "666",
                    "user_login": "YourFavouriteStreamer",
                    "user_name": "YourFavouriteStreamer",
                    "game_id": "The 7th Guest",
                    "game_name": "The 7th Guest",
                    "type": "live",
                    "title": "The best game of all time!",
                    "viewer_count": 1000000,
                    "started_at": "2020-06-22T00:00:00Z",
                    "language": "en",
                    "thumbnail_url": "https://static-cdn.jtvnw.net/previews-ttv/live_user_userlogin-{width}x{height}.jpg",
                    "tag_ids": [],
                    "is_mature": True,
                    "last_seen": "2020-06-22T00:00:00Z"
                }
            ]}
        return {}
    
    
    def ReadGameCache(self, game):
        ret = super().ReadGameCache(game)
        if not ret:
            print('default game cache')
            return {}
        return ret
        
    def ReadStreamerCache(self, streamer):
        ret = super().ReadStreamerCache(streamer)
        if not ret:
            print('default streamer cache')
            return {}
        return ret

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


@typechecked
class TestStreamDetective1(TestStreamDetectiveBase):
    def __init__(self, tester: BaseTestCase, startIteration=0):
        self.ClearCache()
        TestStreamDetectiveBase.__init__(self, tester, startIteration)
        self.test('assertEqual', self.totalTweetsSent, 2, 'totalTweetsSent')
        self.test('assertEqual', self.totalWebhooksSent, 3, 'totalWebhooksSent')
        self.test('assertEqual', self.totalPushbulletsSent, 2, 'totalPushbulletsSent')
        # the config.example.json has 2 Deus Ex Randomizer entries going to defaultDiscord
        self.test('assertEqual', self.totalCooldownsCaught, 1, 'totalCooldownsCaught')


@typechecked
class TestCooldown(TestStreamDetectiveBase):
    def __init__(self, tester: BaseTestCase, startIteration=0):
        if startIteration==0:
            self.ClearCache()
        TestStreamDetectiveBase.__init__(self, tester, startIteration)
    
    def HandleConfigFile(self):
        super().HandleConfigFile()
        if self.iterations == 2:
            self.config['CooldownSeconds'] = -10
        self.config['Searches'] = [{
			"GameName": "Deus Ex",
			"filters": [
				{ "MatchTagName": "Randomizer" },
				{ "MatchString": "rando" }
			],
            "Notifications":[ "defaultDiscord" ]
		}]
        self.TestConfig()
    
    def HandleGame(self, game: dict):
        newStreams = super().HandleGame(game)

        if self.iterations == 1:
            self.test('assertEqual', self.webhooksSent, 1, 'webhooksSent')
            self.test('assertEqual', self.cooldownsCaught, 0, 'cooldownsCaught')
        elif self.iterations == 2:
            self.test('assertEqual', self.webhooksSent, 0, 'webhooksSent')
            self.test('assertEqual', self.cooldownsCaught, 1, 'cooldownsCaught')
        elif self.iterations == 3:
            self.ClearCache()
            self.test('assertEqual', self.webhooksSent, 1, 'webhooksSent')
            self.test('assertEqual', self.cooldownsCaught, 0, 'cooldownsCaught')
        else:
            self.ClearCache()
            self.test('fail', 'Unexpected iteration '+str(self.iterations))


@typechecked
class TestMultiples(TestStreamDetectiveBase):
    def __init__(self, tester: BaseTestCase, startIteration=0):
        self.ClearCache()
        TestStreamDetectiveBase.__init__(self, tester, startIteration)
        self.test('assertEqual', self.totalWebhooksSent, 1, 'totalWebhooksSent')
        self.test('assertEqual', self.totalTweetsSent, 1, 'totalTweetsSent')
    
    def HandleConfigFile(self):
        super().HandleConfigFile()
        self.config['Searches'] = [
            {
                "GameName": "Deus Ex",
                "Notifications":[ "defaultDiscord" ]
            },
            {
                "GameName": "Deus Ex",
                "Notifications":[ "defaultTwitter" ]
            }
        ]
        self.TestConfig()

    def HandleGame(self, game: dict):
        newStreams = super().HandleGame(game)
        print('got', len(newStreams), 'new streams for: ', game)
        self.test('assertEqual', len(newStreams), 1, 'got 1 newStreams')

setVerbose(9)
unittest.main(verbosity=9, warnings="error", failfast=True)
