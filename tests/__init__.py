from typeguard import typechecked, install_import_hook
install_import_hook('libStreamDetective')
import shutil, os, tempfile, json

from libStreamDetective.config import validateSearchesConfig
from libStreamDetective.libStreamDetective import StreamDetective, path
from libStreamDetective.notifiers import Notifier

def GetCacheDir():
    tempDir = os.path.join(tempfile.gettempdir(),"streamstests")
    return tempDir


class TestStreamDetectiveBase(StreamDetective):
    def __init__(self, clearCache=True, **kargs):
        print('\n\n', type(self), '__init__ starting')
        self.cooldownsCaught = 0
        self.tempDir = GetCacheDir()
        self.fetchedGames = {}
        self.fetchedStreamers = {}
        if clearCache:
            self.ClearCache()
        StreamDetective.__init__(self, dry_run=True, tempDir=self.tempDir, **kargs)
        print('\n', type(self), '__init__ done, cooldownsCaught:', self.cooldownsCaught, '\n')


    def FetchAllStreams(self):
        pass


    def HandleConfigFile(self):
        print("Reading default config.json file")
        exampleConfigFileFullPath = os.path.join(path,"config.example.json")
        with open(exampleConfigFileFullPath, 'r') as f:
            self.config = json.load(f)

        exampleSearchFullPath = os.path.join(path,"searches_examples/searches.json.example")
        with open(exampleSearchFullPath, 'r') as f:
            self.config['Searches'] = json.load(f)
            validateSearchesConfig(self.config['Searches'])
        
        # make sure the example config is invalid
        successTestConfig=False
        try:
            self.TestConfig()
            successTestConfig = True
        except:
            pass
        assert not successTestConfig, 'TestConfig should have failed!'

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

    
    def ClearCache(self):
        print('Clearing Cache '+str(type(self)))
        self.tempDir = GetCacheDir()
        if os.path.isdir(self.tempDir):
            shutil.rmtree(self.tempDir)
        if not os.path.exists(self.tempDir):
            os.makedirs(self.tempDir)


    def checkIsOnCooldown(self, stream, webhookUrl):
        if super().checkIsOnCooldown(stream, webhookUrl):
            self.cooldownsCaught+=1
            return True
        return False



class NotifierTest(Notifier):
    def __init__(self, name):
        self.ProfileName = name
        self.dry_run = False
        self.MessagesSent = 0
        self.ErrorsSent = 0
    
    def sendError(self, errMsg):
        print('sendError:', errMsg)

    def GetUserProfilePicUrl(self,userId):
        return ""
