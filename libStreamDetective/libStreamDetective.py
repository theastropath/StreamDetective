import random
from urllib.parse import urlencode
from requests import Session
from requests.adapters import HTTPAdapter
from requests.auth import HTTPBasicAuth
from requests.exceptions import HTTPError, InvalidURL, ConnectionError
import requests
import json
import os.path
from pathlib import Path
import sys
import tempfile
import traceback
from hashlib import sha1
from datetime import datetime
import time
import tweepy
import re
from mastodon import Mastodon

from libStreamDetective.config import validateConfig, validateSearchesConfig
from libStreamDetective.util import *
from libStreamDetective.notifiers import CreateNotifier

path = os.path.realpath(os.path.dirname(__file__))
path = os.path.dirname(path)

configFileName="config.json"
searchesFolderPath="searches"
cacheFileName="cache.json"


class StreamDetective:
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
        self.session=Session()
        retryAdapter = HTTPAdapter(max_retries=2)
        self.session.mount('https://',retryAdapter)
        self.session.mount('http://',retryAdapter)

        self.streamsUrl='https://api.twitch.tv/helix/streams?'
        self.usersUrl='https://api.twitch.tv/helix/users?'
        self.gameIdUrlBase='https://api.twitch.tv/helix/games?'
        
        self.gameIdCache={}
        self.gameArtCache={}
        self.cooldowns={}
        self.notifiers={}
        self.LoadCacheFiles()
        
        self.rateLimitLimit=None
        self.rateLimitRemaining=None
        self.rateLimitReset=None
        self.apiCalls=0
        
        if self.HandleConfigFile():
            print("Created default config.json file")
            exit(0)

        for NotifierConfig in self.config.get("NotificationServices", []):
            self.AddNotifier(NotifierConfig)
        
        if testStream:
            print("\n\nUsing testStream", testStream)
            testStream['game_id'] = self.GetGameId(testStream['game_name'])
            self.fetchedStreamers = [testStream]
            self.fetchedGames = {}
            self.fetchedGames[testStream["game_id"]] = [testStream]
        else:
            self.FetchAllStreams()

        if checkUser:
            self.CheckUser(checkUser)
            return
        
        self.HandleSearches()
        
        self.SaveCacheFiles()
        
        if self.rateLimitLimit is not None and self.rateLimitReset is not None:
            #Output rate limit info
            print("Rate Limit: "+str(self.rateLimitRemaining)+"/"+str(self.rateLimitLimit)+" - Resets at "+datetime.fromtimestamp(self.rateLimitReset).strftime('%c'))
        print("Number of API Calls: "+str(self.apiCalls))
         
    def FetchAllStreams(self):
        gameNames = []
        streamers = []
        
        for streamer in self.config.get('Streamers',[]):
            name = streamer["UserName"]
            if name not in streamers:
                streamers.append(name)
                
        for game in self.config.get('Games',[]):
            name = game["GameName"]
            if name not in gameNames:
                gameNames.append(name)
                
        for search in self.config.get('Searches',[]):
            if "GameName" in search:
                name = search["GameName"]
                if name not in gameNames:
                    gameNames.append(name)
            elif "UserName" in search:
                name = search["UserName"]
                if name not in streamers:
                    streamers.append(name)
                
        #print("All Games: "+str(gameNames))
        #print("All Streamers: "+str(streamers))
        self.fetchedGames = {}
        self.fetchedStreamers = []
        
        #This should be extended to handle more than 100 unique games
        if gameNames:
            allGamesUrl = self.streamsUrl
            for game in gameNames:
                gameId = self.GetGameId(game)
                allGamesUrl += "game_id="+gameId+"&"
            #print("All games: "+allGamesUrl)
            fetchedGames = self.GetAllStreams(allGamesUrl)
            
            #This will be presorted so that we only have to go through the list once
            self.fetchedGames = {}
            
            for game in fetchedGames:
                if game["game_id"] not in self.fetchedGames:
                    self.fetchedGames[game["game_id"]] = []
                self.fetchedGames[game["game_id"]].append(game)
                
            
        #This should be extended to handle more than 100 unique streamers    
        if streamers:
            allStreamersUrl = self.streamsUrl
            for streamer in streamers:
                allStreamersUrl += "user_login="+streamer+"&"
            self.fetchedStreamers = self.GetAllStreams(allStreamersUrl)

    
    def CheckUser(self, user):
        for s in self.fetchedStreamers:
            if s['user_name'] == user:
                print('found', user, s)
                return True
        
        for g in self.fetchedGames.values():
            for s in g:
                if s['user_name'] == user:
                    print('found', user, s)
                    return True

        url = self.streamsUrl + 'user_login='+user
        self.fetchedStreamers = self.GetAllStreams(url)
        for s in self.fetchedStreamers:
            if s['user_name'] == user:
                print('found', user, s)
                return True
        return False
            
    
    def TestConfig(self):
        validateConfig(self.config)
        for i in range(len(self.config.get('IgnoreStreams', []))):
            self.config['IgnoreStreams'][i] = self.config['IgnoreStreams'][i].lower()


    def HandleConfigFile(self):
        configFileFullPath = os.path.join(path,configFileName)
        if os.path.exists(configFileFullPath):
            with open(configFileFullPath, 'r') as f:
                self.config = json.load(f)
            
            if 'Searches' not in self.config:
                self.config['Searches'] = []

            configsFolder = Path(path) / searchesFolderPath
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
                    self.HandleGame(search)
                except Exception as e:
                    logex(self, e, 'error in', search)
            elif "UserName" in search:
                try:
                    self.HandleStreamer(search)
                except Exception as e:
                    logex(self, e, 'error in', search)
                



    def TwitchApiRequest(self, url, headers={}):
        debug('TwitchApiRequest', url, headers)
        response = None

        if self.apiCalls > 200:
            raise Exception('too many Twitch API calls', self.apiCalls)
        if self.rateLimitRemaining is not None and self.rateLimitRemaining < 10:
            raise Exception('rate limit remaining is too low', self.rateLimitRemaining)
    
        try:
            headers = {
                'Client-ID': self.config["clientId"],
                'Authorization': 'Bearer '+self.config["accessToken"],
                'Content-Type': 'application/json',
                **headers
            }
            response = self.session.get(url, headers=headers)
            self.apiCalls+=1
            trace(url, response.headers, response.text)
            result = json.loads(response.text)
        except Exception as e:
            logex(self, e, 'request for '+url+' failed: ')
            raise

        if not result:
            if response and response.headers:
                print(repr(response.headers))
            print('request for '+url+' failed')
            raise Exception('request failed')
        if 'status' in result and result['status'] != 200:
            if response and response.headers:
                print(repr(response.headers))
            print('request for '+url+' failed with status:', result['status'], ', result: ', result)
            raise Exception('request for '+url+' failed with status:', result['status'], ', result: ', result)
        if response and response.headers:
            #hdrs=json.loads(response.headers)
            debug('TwitchApiRequest','Ratelimit-Limit', response.headers["Ratelimit-Limit"])
            self.rateLimitLimit = int(response.headers["Ratelimit-Limit"])
            debug('TwitchApiRequest','Ratelimit-Remaining', response.headers["Ratelimit-Remaining"])
            self.rateLimitRemaining = int(response.headers["Ratelimit-Remaining"])
            debug('TwitchApiRequest','Ratelimit-Reset', response.headers["Ratelimit-Reset"])
            self.rateLimitReset = int(response.headers["Ratelimit-Reset"])
            
        debug('TwitchApiRequest', 'results:', len(result.get('data', [])))
        return result

    def SaveCacheFiles(self):
        cacheFileFullPath = os.path.join(self.tempDir,cacheFileName)

        with open(cacheFileFullPath, 'w') as f:
            cache = { 'gameIds': self.gameIdCache,
                'gameArt': self.gameArtCache,
                'cooldowns': self.cooldowns
            }
            json.dump(cache,f,indent=4)
        
    def LoadCacheFiles(self):
        cacheFileFullPath = os.path.join(self.tempDir,cacheFileName)
        try:
            if os.path.exists(cacheFileFullPath):
                with open(cacheFileFullPath, 'r') as f:
                    cache = json.load(f)
                    self.gameIdCache = cache.get('gameIds',{})
                    self.gameArtCache = cache.get('gameArt',{})
                    self.cooldowns = cache.get('cooldowns',{})
        except Exception as e:
            logex(self, e, 'error in LoadCacheFile ', cacheFileFullPath)


    def AddGameIdToCache(self,gameName,gameId):
        self.gameIdCache[gameName]=gameId

    def AddGameArtToCache(self,gameName,artUrl):
        self.gameArtCache[gameName]=artUrl

    def GetGameId(self, gameName):
        if gameName in self.gameIdCache:
            return self.gameIdCache[gameName]
    
        gameIdUrl = self.gameIdUrlBase+"name="+gameName
        gameId = 0
        boxArt = ""

        result = self.TwitchApiRequest(gameIdUrl)

        if "data" in result and len(result["data"])==1:
            gameId = result["data"][0]["id"]
            boxArt = result["data"][0]["box_art_url"].replace("{width}","144").replace("{height}","192")
        else:
            raise Exception(gameIdUrl+" response expected 1 game id: ", result)

        if not gameId:
            raise Exception('gameId is missing')
            
        if gameId:
            self.AddGameIdToCache(gameName,gameId)
            
        if boxArt:
            self.AddGameArtToCache(gameName,boxArt)
            
        return gameId

    def GetAllGameStreams(self,gameId):
        return self.fetchedGames.get(str(gameId),[])
                
    def GetAllStreamerStreams(self,streamer):
        for stream in self.fetchedStreamers:
            if stream["user_login"].lower()==streamer.lower():
                return [stream]
        return []
        
    def GetAllStreams(self,lookupUrl):
        allStreams = []
        keepGoing = True
        cursor = ""
        while keepGoing:
            url = lookupUrl
            if not lookupUrl.endswith('&'):
                url += '&'
            url += "first=100" # Fetch 100 streams at a time
            
            if cursor!="":
                url+="&after="+cursor
            
            result = None
            result = self.TwitchApiRequest(url)
            # Twitch API doesn't always return full pages, so we need to load the next page no matter what
            if "pagination" in result and "cursor" in result["pagination"]:
                keepGoing = True
                cursor = result["pagination"]["cursor"]
            else:
                keepGoing = False
                cursor = ""
                
                
            for stream in result['data']:
                allStreams.append(stream)
                #print(stream["user_login"])
                
            if keepGoing:
                time.sleep(0.1) # pace yourself a little bit
            
        return allStreams        
    
    def GetFilter(self, filter, name) -> list:
        f = filter.get(name, [])
        if not isinstance(f, list):
            f = [f]
        return f
    

    def CheckStreamFilter(self, filter, streamer, title, tags, gameName):
        if not filter.keys():
            return True

        if not tags:
            tags = []

        for f in self.GetFilter(filter, 'MatchTag'):
            if f.lower() not in tags:
                return False
        for f in self.GetFilter(filter, 'MatchTagName'):
            if f.lower() not in tags:
                return False
        for f in self.GetFilter(filter, 'MatchTagSubstring'):
            found=False
            for tag in tags:
                if f.lower() in tag:
                    found=True
            if not found:
                return False
        for f in self.GetFilter(filter, 'MatchString'):
            if f.lower() not in title.lower():
                return False
        for f in self.GetFilter(filter, 'DontMatchTag'):
            if f.lower() in tags:
                return False
        for f in self.GetFilter(filter, 'DontMatchString'):
            if f.lower() in title.lower():
                return False
        for f in self.GetFilter(filter, 'DontMatchTagName'):
            if f.lower() in tags:
                return False
        for f in self.GetFilter(filter, 'DontMatchTagSubstring'):
            found=False
            for tag in tags:
                if f.lower() in tag:
                    found=True
            if found:
                return False
        for f in self.GetFilter(filter, 'MatchGameName'):
            if f != gameName:
                return False
        for f in self.GetFilter(filter, 'DontMatchGameName'):
            if f == gameName:
                return False
        for f in self.GetFilter(filter, 'DontMatchUser'):
            if f.lower() == streamer.lower():
                return False
            
        for f in self.GetFilter(filter, 'SearchRegex'):
            found = False
            if re.search(f, title, flags=re.IGNORECASE):
                found = True
            if not found:
                return False
            
        for f in self.GetFilter(filter, 'DontSearchRegex'):
            if re.search(f, title, flags=re.IGNORECASE):
                return False

        return True

    def CheckStream(self, entry, streamer, title, tags, gameName):
        trace("Name: ", streamer, title)
        if not entry.get('filters'):
            # return True if the filters array is empty, or the key is missing
            return True
        
        if tags:
            tags=[x.lower() for x in tags]
        
        for filter in entry['filters']:
            if self.CheckStreamFilter(filter, streamer, title, tags, gameName):
                return True
        return False

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

    def HandleStreamer(self,streamer):
        print("Handling "+streamer["UserName"])
      
        streamInfo = self.ReadStreamerCache(streamer)
        hadCache = True
        if streamInfo is None:
            streamInfo = {}
            hadCache = False
        newStreams = []

        allStreams = self.GetAllStreamerStreams(streamer["UserName"])
        now = datetime.now()

        for stream in allStreams:
            id = stream['id']
            userlogin = stream['user_login']
            title = stream['title']
            tags = stream['tags']
            stream['last_seen'] = now.isoformat()
            matched = self.CheckStream(streamer, userlogin, title, tags, stream["game_name"])
            if matched:
                debug("matched "+userlogin)
                stream['last_matched'] = now.isoformat()
                if id not in streamInfo:
                    newStreams.append(stream)
            else:
                trace('didn\'t match', userlogin)
 
        # All stream info now retrieved
        if hadCache and newStreams:
            print("  New Streams: "+str([stream['user_login'] for stream in newStreams]))
            
            self.genNotifications(newStreams,streamer)
            for stream in newStreams:
                id = stream['id']
                streamInfo[id] = stream
        elif not hadCache:
            newStreams = []
            print("Old streams cache not found, creating it now")
            
        # cleanup old entries in cache
        toDelete = []
        for key, val in streamInfo.items():
            last_seen = fromisoformat(val['last_seen'])
            if (now - last_seen).total_seconds() > (3600*24):
                toDelete.append(key)

        for key in toDelete:
            del streamInfo[key]

        if not os.path.exists(self.tempDir):
            os.makedirs(self.tempDir)

        self.WriteStreamerCache(streamer, streamInfo)
        debug("\n\n")
        return newStreams


    def HandleGame(self,game):
        print("Handling "+game["GameName"])
        gameId = self.GetGameId(game["GameName"])

        streamInfo = self.ReadGameCache(game)
        hadCache = True
        if streamInfo is None:
            streamInfo = {}
            hadCache = False
        newStreams = []
        
        allStreams = self.GetAllGameStreams(gameId)

        now = datetime.now()

        for stream in allStreams:
            id = stream['id']
            streamer = stream['user_login']
            title = stream['title']
            tags = stream['tags']
            stream['last_seen'] = now.isoformat()
            matched = self.CheckStream(game, streamer, title, tags, stream["game_name"])
            if matched:
                debug("matched "+streamer)
                stream['last_matched'] = now.isoformat()
                if id not in streamInfo:
                    newStreams.append(stream)
            else:
                trace('didn\'t match', streamer)
                
        # All stream info now retrieved
        if hadCache and newStreams:
            print("  New Streams: "+str([stream['user_login'] for stream in newStreams]))
            
            #New style
            self.genNotifications(newStreams,game)
            for stream in newStreams:
                id = stream['id']
                streamInfo[id] = stream
        elif not hadCache:
            newStreams = []
            print("Old streams cache not found, creating it now")
            
        # cleanup old entries in cache
        toDelete = []
        for key, val in streamInfo.items():
            last_seen = fromisoformat(val['last_seen'])
            if (now - last_seen).total_seconds() > (3600*24):
                toDelete.append(key)

        for key in toDelete:
            del streamInfo[key]

        if not os.path.exists(self.tempDir):
            os.makedirs(self.tempDir)

        self.WriteGameCache(game, streamInfo)
        debug("\n\n")
        return newStreams


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


    def getGameBoxArt(self,gameName,width,height):
        if gameName in self.gameArtCache:
            return self.gameArtCache[gameName]

        gameUrl = "https://api.twitch.tv/helix/games?name="+gameName
        
        result = self.TwitchApiRequest(gameUrl)
        if result.get('data') and result["data"][0].get('box_art_url'):
            url = result["data"][0]["box_art_url"]
            url = url.replace("{width}",str(width)).replace("{height}",str(height))
            self.AddGameArtToCache(gameName,url)
            return url
        return ""


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



verbose = 1
debug = print
trace = print

def setVerbose(v: int):
    global debug, trace
    verbose = v
    if verbose:
        debug = print
        trace = print
    else:
        debug = lambda *a: None # do-nothing function
        trace = debug
    
    if verbose >= 2:
        trace = print
    else:
        trace = lambda *a: None # do-nothing function

def getVerbose() -> int:
    global verbose
    return verbose

setVerbose(verbose)
