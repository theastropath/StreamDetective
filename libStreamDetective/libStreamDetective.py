import json
import os.path
from pathlib import Path
import tempfile
from hashlib import sha1
from datetime import datetime
import re

from libStreamDetective import db, filters, searches
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

    def __init__ (self, dry_run=False, testStream=None, checkUser=None, searchFile=None):
        print('\n\n'+datetime.now().isoformat()+': StreamDetective starting')
        db.connect('sddb.sqlite3')
        
        if dry_run:
            print('dry-run is enabled')
        self.dry_run = dry_run
        
        self.notifiers={}
        
        if self.HandleConfigFile(searchFile):
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
            self.CheckSingleUser(checkUser)
            return
        
        self.HandleSearches()
        print('')
    

    def FetchAllStreams(self):
        searchProviders = AllProviders(self.config)
        for search in self.config.get('Searches',[]):
            if 'GameName' in search:
                searchProviders.AddGame(search['GameName'])
            elif 'UserName' in search:
                searchProviders.AddUser(search['UserName'])
            elif search.get('SearchAll') or search.get('SearchTags'): # this one is a boolean
                searchProviders.SearchAll()
        
        (self.fetchedGames, self.fetchedAll, self.fetchedStreamers) = searchProviders.FetchAllStreams()
    
    
    def CheckSingleUser(self, user):# for CLI
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
        (fetchedGames, fetchedAll, fetchedStreamers) = searchProviders.FetchAllStreams()

        if user in fetchedStreamers:
            print('found', user, s)
            return True
        return False
            
    
    def TestConfig(self):
        validateConfig(self.config)
        for i in range(len(self.config.get('IgnoreStreams', []))):
            self.config['IgnoreStreams'][i] = self.config['IgnoreStreams'][i].lower()


    def HandleConfigFile(self, globPattern='*.json'):
        configFileFullPath = os.path.join(path, self.configFileName)
        if os.path.exists(configFileFullPath):
            with open(configFileFullPath, 'r') as f:
                self.config = json.load(f)
            
            if 'Searches' not in self.config:
                self.config['Searches'] = []

            configsFolder = Path(path) / self.searchesFolderPath
            if not globPattern:
                globPattern='*.json'
            for f in configsFolder.glob(globPattern):
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
        self.notifiers[name] = CreateNotifier(config, self.dry_run)


    def HandleSearches(self):
        for search in self.config.get("Searches",[]):
            if "GameName" in search:
                debug('Handling', search["GameName"])
                streams = self.GetAllGameStreams(search["GameName"])
            elif "UserName" in search:
                debug('Handling', search['UserName'])
                streams = self.GetAllStreamerStreams(search['UserName'])
            elif "SearchTags" in search:
                debug('Handling', search['SearchTags'])
                streams = self.GetAllStreams()
            elif search.get('SearchAll'): # this one is a boolean
                debug('Handling search all', search.get('filters'))
                streams = self.GetAllStreams()
            else:
                print('unknown search type', search)
                continue
            try:
                searches.HandleFilters(self, search, streams)
            except Exception as e:
                logex(self, e, 'error in', search)


    def GetAllGameStreams(self,gameName) -> list:
        return self.fetchedGames.get(gameName.lower(),[])
    
    def GetAllStreams(self) -> list:
        return self.fetchedAll
    
    def GetAllStreamerStreams(self,streamer) -> list:
        streamer = streamer.lower()
        if streamer in self.fetchedStreamers:
            return [self.fetchedStreamers[streamer]]
        return []

    def CheckStream(self, entry, streamer, title, tags, gameName):
        return filters.CheckStream(entry, streamer, title, tags, gameName)
    

    @staticmethod
    def GetSearchId(profile):
        profileHash = json.dumps(profile)
        profileHash = sha1(profileHash.encode()).hexdigest()
        return profileHash


    def genNotifications(self, newStreams, entry):
        notifications = entry.get("Notifications",[])
        for NotifierName in notifications:
            notifier = self.notifiers.get(NotifierName)
            notifierData = None
            if isinstance(notifications, dict):
                notifierData = notifications.get(NotifierName)
            if notifier:
                self.triggerNotifier(notifier, notifierData, entry, newStreams)
    

    def triggerNotifier(self, notifier, notifierData, entry, newStreams):
        profileName = notifier.ProfileName
        toSend = self.filterIgnoredStreams(profileName, newStreams)
        if toSend:
            notifier.handleSingleNotificationService(notifierData, entry, toSend)


    def genErrorMsgs(self,errMsg):
        notifications = self.config.get("ErrorNotifications",[])
        for NotifierName in notifications:
            notifier = self.notifiers.get(NotifierName)
            if notifier:
                notifier.handleErrorSingleNotificationService(errMsg)


    def filterIgnoredStreams(self,profileName,newStreams):
        IgnoreStreams = self.config.get('IgnoreStreams', [])
        toSend = []
        onCooldown = []
        for stream in newStreams:
            if stream["user_login"].lower() in IgnoreStreams:
                debug(stream["user_login"], 'is in IgnoreStreams')
                continue
            if self.checkIsOnCooldown(stream, profileName):
                onCooldown.append(stream["user_login"])
                continue
            toSend.append(stream)
        if onCooldown:
            print('      On cooldown for', profileName, ':', onCooldown)
        return toSend


    def checkIsOnCooldown(self, stream, ProfileName) -> bool:
        user = stream["user_login"].lower()
        key = user + '-' + ProfileName
        CooldownSeconds = self.config.get('CooldownSeconds',0)
        now = unixtime()
        res = db.fetchone('SELECT * FROM cooldowns WHERE streamer=? AND notifier=? AND last>?', (user, ProfileName, now-CooldownSeconds))
        db.upsert('cooldowns', dict(streamer=user, notifier=ProfileName, last=now))
        if res:
            debug('      ', user, 'is on cooldown for', ProfileName)
            return True
        return False

