import json
import os.path
from pathlib import Path
import tempfile
from hashlib import sha1
from datetime import datetime
import re

from libStreamDetective import filters, searches
from libStreamDetective.twitch import TwitchApi
from libStreamDetective.searchProviders import AllProviders
from libStreamDetective.config import validateConfig, validateSearchesConfig
from libStreamDetective.util import *
from libStreamDetective.notifiers import CreateNotifier

path = os.path.realpath(os.path.dirname(__file__))
path = os.path.dirname(path)

class StreamDetective:
    configFileName="config.json"
    searchesFolderPath="searches"
    cacheFileName="cache.json"

    def __init__ (self, dry_run=False, tempDir=None, testStream=None, checkUser=None):
        print(datetime.now().isoformat()+': StreamDetective starting')

        if tempDir:
            self.tempDir = tempDir
        else:
            self.tempDir = os.path.join(tempfile.gettempdir(),"streams")
        
        if not os.path.exists(self.tempDir):
            os.makedirs(self.tempDir)
        
        if dry_run:
            print('dry-run is enabled')
        self.dry_run = dry_run
        
        self.cooldowns={}
        self.notifiers={}
        self.LoadCacheFiles()
        
        if self.HandleConfigFile():
            print("Created default config.json file")
            exit(0)

        for NotifierConfig in self.config.get("NotificationServices", []):
            self.AddNotifier(NotifierConfig)
        
        if testStream:
            print("\n\nUsing testStream", testStream)
            self.fetchedStreamers = {}
            self.fetchedStreamers[testStream['user_login'].lower()] = testStream
            self.fetchedGames = {}
            self.fetchedGames[testStream["game_name"].lower()] = [testStream]
        else:
            self.FetchAllStreams()

        if checkUser:
            self.CheckUser(checkUser)
            return
        
        self.HandleSearches()
        
        self.SaveCacheFiles()


    def FetchAllStreams(self):
        searchProviders = AllProviders(self.config)
        for search in self.config.get('Searches',[]):
            if 'GameName' in search:
                searchProviders.AddGame(search['GameName'])
            elif 'UserName' in search:
                searchProviders.AddUser(search['UserName'])
        
        (self.fetchedGames, self.fetchedStreamers) = searchProviders.FetchAllStreams()
    
    
    def CheckUser(self, user):
        user = user.lower()
        if user in self.fetchedStreamers:
            print('found', user, self.fetchedStreamers[user])
            return True
        
        for g in self.fetchedGames.values():
            for s in g:
                if s['user_name'] == user:
                    print('found', user, s)
                    return True
                
        searchProviders = AllProviders(self.config)
        searchProviders.AddUser(user)
        (fetchedGames, fetchedStreamers) = searchProviders.FetchAllStreams()

        if user in fetchedStreamers:
            print('found', user, s)
            return True
        return False
            
    
    def TestConfig(self):
        validateConfig(self.config)
        for i in range(len(self.config.get('IgnoreStreams', []))):
            self.config['IgnoreStreams'][i] = self.config['IgnoreStreams'][i].lower()


    def HandleConfigFile(self):
        configFileFullPath = os.path.join(path, self.configFileName)
        if os.path.exists(configFileFullPath):
            with open(configFileFullPath, 'r') as f:
                self.config = json.load(f)
            
            if 'Searches' not in self.config:
                self.config['Searches'] = []

            configsFolder = Path(path) / self.searchesFolderPath
            for f in configsFolder.glob('*.json'):
                try:
                    data = f.read_text()
                    searches = json.loads(data)
                    validateSearchesConfig(searches)
                    self.config['Searches'].extend(searches)
                except Exception as e:
                    e.add_note('error in file: ' + str(f))
                    raise e
            
            try:
                self.TestConfig()
            except AssertionError as e:
                self.genErrorMsgs("Config validation failed: "+str(e))
                raise
        
        else:
            print("Writing default config.json file")
            config = {}
            exampleConfigFileFullPath = os.path.join(path,"config.example.json")
            with open(exampleConfigFileFullPath, 'r') as f:
                config = json.load(f)
            
            with open(configFileFullPath, 'w') as f:
                json.dump(config,f, indent=4)

            return True


    def AddNotifier(self, config):
        name = config['ProfileName']
        assert name not in self.notifiers
        self.notifiers[name] = CreateNotifier(config, self)


    def HandleSearches(self):
        for search in self.config.get("Searches",[]):
            if "GameName" in search:
                try:
                    searches.HandleGame(self, search)
                except Exception as e:
                    logex(self, e, 'error in', search)
            elif "UserName" in search:
                try:
                    searches.HandleStreamer(self, search)
                except Exception as e:
                    logex(self, e, 'error in', search)
                

    def SaveCacheFiles(self):
        cacheFileFullPath = os.path.join(self.tempDir, self.cacheFileName)

        with open(cacheFileFullPath, 'w') as f:
            cache = {
                'gameIds': TwitchApi.gameIdCache,
                'gameArt': TwitchApi.gameArtCache,
                'cooldowns': self.cooldowns
            }
            json.dump(cache,f,indent=4)
        
    def LoadCacheFiles(self):
        cacheFileFullPath = os.path.join(self.tempDir, self.cacheFileName)
        try:
            if os.path.exists(cacheFileFullPath):
                with open(cacheFileFullPath, 'r') as f:
                    cache = json.load(f)
                    TwitchApi.gameIdCache = cache.get('gameIds',{})
                    TwitchApi.gameArtCache = cache.get('gameArt',{})
                    self.cooldowns = cache.get('cooldowns',{})
        except Exception as e:
            logex(self, e, 'error in LoadCacheFile ', cacheFileFullPath)


    def GetAllGameStreams(self,gameName) -> list:
        return self.fetchedGames.get(gameName.lower(),[])
    
    def GetAllStreamerStreams(self,streamer) -> list:
        streamer = streamer.lower()
        if streamer in self.fetchedStreamers:
            return [self.fetchedStreamers[streamer]]
        return []

    def CheckStream(self, entry, streamer, title, tags, gameName):
        return filters.CheckStream(entry, streamer, title, tags, gameName)

    def GetCachePath(self, name, profile):
        profileHash = json.dumps(profile)
        profileHash = sha1(profileHash.encode()).hexdigest()
        cacheName = name + '-' + profileHash
        cacheName = re.sub('[^\w\d ]', '-', cacheName)
        return os.path.join(self.tempDir, cacheName)
    
    def ReadGameCache(self, game):
        saveLocation = self.GetCachePath(game["GameName"], game)
        if os.path.exists(saveLocation):
            try:
                f = open(saveLocation,'r')
                streamInfoOld = json.load(f)
                f.close()
                return streamInfoOld
            except Exception as e:
                logex(self, e, 'ReadGameCache failed at:', saveLocation, ', with config:', game)
        return None
        
    def ReadStreamerCache(self, streamer):
        saveLocation = self.GetCachePath(streamer["UserName"], streamer)
        if os.path.exists(saveLocation):
            try:
                f = open(saveLocation,'r')
                streamInfoOld = json.load(f)
                f.close()
                return streamInfoOld
            except Exception as e:
                logex(self, e, 'ReadStreamerCache failed at:', saveLocation, ', with config:', streamer)
        return None

    def WriteGameCache(self, game, streamInfo):
        saveLocation = self.GetCachePath(game["GameName"], game)
        f = open(saveLocation,'w')
        json.dump(streamInfo,f,indent=4)
        f.close()    
        
    def WriteStreamerCache(self, streamer, streamInfo):
        saveLocation = self.GetCachePath(streamer["UserName"], streamer)
        f = open(saveLocation,'w')
        json.dump(streamInfo,f,indent=4)
        f.close()


    def genNotifications(self, newStreams, entry):
        notifications = entry.get("Notifications",[])

        for NotifierName in notifications:
            notifier = self.notifiers.get(NotifierName)
            if notifier:
                notifier.handleSingleNotificationService(entry, newStreams)
    

    def genErrorMsgs(self,errMsg):
        notifications = self.config.get("ErrorNotifications",[])

        for NotifierName in notifications:
            notifier = self.notifiers.get(NotifierName)
            if notifier:
                notifier.handleErrorSingleNotificationService(errMsg)


    def filterIgnoredStreams(self,profileName,newStreams):
        IgnoreStreams = self.config.get('IgnoreStreams', [])
        
        toSend = []
        for stream in newStreams:
            if stream["user_login"].lower() in IgnoreStreams:
                debug(stream["user_login"], 'is in IgnoreStreams')
                continue
            if self.checkIsOnCooldown(stream, profileName):
                continue
            toSend.append(stream)
        return toSend


    def checkIsOnCooldown(self, stream, ProfileName) -> bool:
        user = stream["user_login"].lower()
        key = user + '-' + ProfileName
        now = datetime.now()
        cooldown = self.cooldowns.get(key)
        if not cooldown:
            self.cooldowns[key] = { 'last_notified': now.isoformat() }
            return False
        last_notified = cooldown['last_notified']
        last_notified = fromisoformat(last_notified)
        if (now - last_notified).total_seconds() < self.config.get('CooldownSeconds',0):
            print(stream["user_login"], 'is on cooldown for', ProfileName)
            return True
        cooldown['last_notified'] = now.isoformat()
        return False
