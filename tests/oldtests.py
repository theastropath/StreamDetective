import autoinstaller
from typeguard import typechecked, install_import_hook
install_import_hook('libStreamDetective')
import libStreamDetective.twitch
from libStreamDetective.libStreamDetective import *
from libStreamDetective import notifiers
import shutil
import unittest

failures = []

currentTester = None
def MockTwitchApiRequest(url, headers={}):
    global currentTester
    self = currentTester
    self.twitchApiCalls += 1
    streamsUrl = libStreamDetective.twitch.TwitchApi.streamsUrl
    print('mocked TwitchApiRequest', self, url, headers)
    self.tester.assertEqual(type(headers), dict)
    ret = []
    if streamsUrl in url and 'game_id=' in url:
        self.getStreamsApiCalls += 1
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
                "tags": ["StreamDetectiveTest"],
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
                "tags": [],
                "is_mature": True,
                "last_seen": "2020-06-22T00:00:00Z"
            })
    elif streamsUrl in url and 'user_login=YourFavouriteStreamer' in url:
        self.getStreamsApiCalls += 1
        ret = [
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
                "tags": [],
                "is_mature": True,
                "last_seen": "2020-06-22T00:00:00Z"
            }
        ]
    print(ret)
    print('end mocked TwitchApiRequest', self, url, headers)
    return { 'data': ret }

def MockGetGameId(gameName=None):
    print('mocked GetGameId', gameName)
    gameId = gameName
    TwitchApi.AddGameIdToCache(gameName,gameId)
    TwitchApi.AddGameArtToCache(gameName,'boxArt')
    return gameId

libStreamDetective.twitch.TwitchApi.Request = MockTwitchApiRequest
libStreamDetective.twitch.TwitchApi.GetGameId = MockGetGameId

@typechecked
class BetterAssertionError(AssertionError):
    def __init__(self, *args):
        global failures
        AssertionError.__init__(self, *args)
        failures.append(self)
        logex(None, self)


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
        # this doesn't work in Python 3.11, _outcome doesn't have errors
        #for error in self._outcome.errors:
        #    if error[1]:
        #        numDetectedErrors+=1
        if numDetectedErrors==0:
            for fail in failures:
                logex(None, fail, 'caught failure')
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

    def test_args(self):
        sd = TestStreamDetectiveBase(self, 0, clearCache=True, testStream=TestStream({
            'game': "Deus Ex", "user": "Heinki", "title": "Deus Ex Randomizer", "tags": ["StreamDetectiveTest"]
        }))
        sd.test('assertEqual', sd.notifiers['defaultDiscord'].MessagesSent, 1, 'totalWebhooksSent')
        online = sd.CheckUser('Heinki')
        self.verboseAssert(self, 'assertEqual', online, True, 'Heinki is online')

    def test_config(self):
        TestStreamDetectiveConfig(self)
    
    def test_example_configs(self):
        sd = TestStreamDetectiveFilters(self)
        sd.assertMatch('Deus Ex', 'Die4Ever2011', 'Deus Ex Randomizer speedruns', [])
        sd.assertMatch('Deus Ex', 'Die4Ever2011', 'dEUS eX rAndomiZer speedruns', [])
        sd.assertNotMatch('Deus Ex', 'Die4Ever2011', 'Deus Ex Rnadomizer speedruns', [])
        sd.assertMatch('StarCraft II', 'zergbonjwa', 'SC2 Randomizer', [])
        sd.assertNotMatch('StarCraft II', 'zergbonjwa', 'SC2 Randomizer Archipelago', [])
        sd.assertMatch('Retro', 'letsplays', 'The 7th Guest', [])
        sd.assertNotMatch('Retro', 'letsplays', 'The Guest', [])


def GetCacheDir():
    tempDir = os.path.join(tempfile.gettempdir(),"streamstests")
    return tempDir


@typechecked
class TestStreamDetectiveConfig(StreamDetective):
    def __init__(self, tester: BaseTestCase, startIteration=0, **kargs):
        print('\n\n', type(self), '__init__ starting')
        configFileFullPath = os.path.join(path, self.configFileName)
        searchesPath = os.path.join(path, self.searchesFolderPath)
        self.dry_run = True
        self.notifiers = {}
        #oldverbose = getVerbose()
        #setVerbose(0)
        if not os.path.exists(configFileFullPath):
            print('no config.json file, skipping test')
        elif not os.path.exists(searchesPath):
            print('no searches folder, skipping test')
        else:
            self.HandleConfigFile()
            #StreamDetective.__init__(self, dry_run=True)
        #setVerbose(oldverbose)


@typechecked
class TestNotifier(notifiers.Notifier):
    def __init__(self, config, parent, name):
        self.name = name
        super().__init__(config, parent)

    def handleMsgs(self, entry, filteredStreams):
        print(self.name, entry, 'handleMsgs', filteredStreams)

    def sendError(self, errMsg):
        print(self.name, 'sendError', errMsg)


@typechecked
class TestStreamDetectiveBase(StreamDetective):
    def __init__(self, tester: BaseTestCase, startIteration=0, **kargs):
        global currentTester
        print('\n\n', type(self), '__init__ starting')
        currentTester = self
        self.tester = tester
        self.totalCooldownsCaught = 0
        self.twitchApiCalls = 0
        self.getStreamsApiCalls = 0
        self.tempDir = GetCacheDir()
        self.iterations = startIteration
        if kargs.get('clearCache'):
            self.ClearCache()
            kargs.pop('clearCache')
        StreamDetective.__init__(self, dry_run=False, tempDir=self.tempDir, **kargs)
        print('\n', type(self), '__init__ done\n')

    def test(self, testname:str, *args):
        self.tester.verboseAssert(self, testname, *args)

    def AddNotifier(self, config):
        NotifierName = config['ProfileName']
        assert NotifierName not in self.notifiers
        self.notifiers[NotifierName] = TestNotifier(config, self, NotifierName)
        print(repr(self.notifiers))
    
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
        self.cooldownsCaught = 0
        newStreams = searches.HandleGame(self, game)
        self.totalCooldownsCaught += self.cooldownsCaught
        self.iterations += 1
        return newStreams

    def HandleStreamer(self, streamer):
        self.cooldownsCaught = 0
        newStreams = searches.HandleStreamer(self, streamer)
        self.totalCooldownsCaught += self.cooldownsCaught
        return newStreams

    def HandleConfigFile(self):
        print("Reading default config.json file")
        exampleConfigFileFullPath = os.path.join(path,"config.example.json")
        with open(exampleConfigFileFullPath, 'r') as f:
            self.config = json.load(f)

        exampleSearchFullPath = os.path.join(path,"searches_examples/searches.json.example")
        with open(exampleSearchFullPath, 'r') as f:
            self.config['Searches'] = json.load(f)
            validateSearchesConfig(self.config['Searches'])
        
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

        self.config['NotificationServices'][3]['ClientKey'] = "ClientKey"
        self.config['NotificationServices'][3]['ClientSecret'] = "ClientSecret"
        self.config['NotificationServices'][3]['AccessToken'] = "AccessToken"
        self.config['NotificationServices'][3]['BaseURL'] = "BaseURL"

        self.TestConfig()
    
    
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


@typechecked
class TestStreamDetective1(TestStreamDetectiveBase):
    def __init__(self, tester: BaseTestCase, startIteration=0):
        self.ClearCache()
        TestStreamDetectiveBase.__init__(self, tester, startIteration)
        n = self.notifiers
        self.test('assertEqual', n['defaultTwitter'].MessagesSent, 2, 'totalTweetsSent')
        self.test('assertEqual', n['defaultMastodon'].MessagesSent, 2, 'totalTootsSent')
        self.test('assertEqual', n['defaultDiscord'].MessagesSent, 3, 'totalWebhooksSent')
        self.test('assertEqual', n['defaultPushbullet'].MessagesSent, 2, 'totalPushbulletsSent')
        # the config.example.json has 2 Deus Ex Randomizer entries going to defaultDiscord
        self.test('assertEqual', self.totalCooldownsCaught, 0, 'totalCooldownsCaught')


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
        n = self.notifiers

        if self.iterations == 1:
            self.test('assertEqual', n['defaultDiscord'].MessagesSent, 1, 'webhooksSent')
            self.test('assertEqual', self.cooldownsCaught, 0, 'cooldownsCaught')
        elif self.iterations == 2:
            self.test('assertEqual', n['defaultDiscord'].MessagesSent, 0, 'webhooksSent')
            self.test('assertEqual', self.cooldownsCaught, 1, 'cooldownsCaught')
        elif self.iterations == 3:
            self.ClearCache()
            self.test('assertEqual', n['defaultDiscord'].MessagesSent, 1, 'webhooksSent')
            self.test('assertEqual', self.cooldownsCaught, 0, 'cooldownsCaught')
        else:
            self.ClearCache()
            self.test('fail', 'Unexpected iteration '+str(self.iterations))


@typechecked
class TestMultiples(TestStreamDetectiveBase):
    def __init__(self, tester: BaseTestCase, startIteration=0):
        self.ClearCache()
        TestStreamDetectiveBase.__init__(self, tester, startIteration)
        n = self.notifiers
        self.test('assertEqual', n['defaultDiscord'].MessagesSent, 1, 'totalWebhooksSent')
        self.test('assertEqual', n['defaultTwitter'].MessagesSent, 1, 'totalTweetsSent')
    
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

@typechecked
class TestStreamDetectiveFilters(StreamDetective):
    configFileName = "config.example.json"
    searchesFolderPath = "searches_examples"

    def __init__(self, tester):
        self.tester = tester
        return super().__init__(dry_run=True)

    def HandleSearches(self):
        pass

    def FetchAllStreams(self):
        pass

    def test(self, testname:str, *args):
        self.tester.verboseAssert(self, testname, *args)

    def TestConfig(self):
        self.config['clientId'] = '123456789012345678901234567890'
        self.config['accessToken'] = '123456789012345678901234567890'
        self.config['NotificationServices'] = [{
            "ProfileName":"defaultDiscord",
            "Type":"Discord",
            "Webhook":"fakeurl",
            "UserName":"Stream Detective"
        }]
        super().TestConfig()

    def testMatch(self, game, streamer, title, tags):
        count = 0
        for search in self.config.get("Searches",[]):
            if search.get('GameName') == game or search.get('UserName') == streamer:
                count += 1
                matched = self.CheckStream(search, streamer, title, tags, game)
                if matched:
                    return True
        if count == 0:
            print("testMatch no filters checked?", game, streamer, title, tags, self.config.get("Searches"))
        return False
    
    def assertMatch(self, game, streamer, title, tags):
        matched = self.testMatch(game, streamer, title, tags)
        self.test('assertTrue', matched, 'filters assertMatch ' + title)

    def assertNotMatch(self, game, streamer, title, tags):
        matched = self.testMatch(game, streamer, title, tags)
        self.test('assertFalse', matched, 'filters assertNotMatch ' + title)
