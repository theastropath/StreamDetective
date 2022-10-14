from urllib.parse import urlencode
from requests import Session
from requests.adapters import HTTPAdapter
from requests.auth import HTTPBasicAuth
from requests.exceptions import HTTPError, InvalidURL, ConnectionError
import requests
import json
import os.path
import sys
import tempfile
import traceback
from hashlib import sha1
from datetime import datetime
import time
import tweepy
import re

path = os.path.realpath(os.path.dirname(__file__))
path = os.path.dirname(path)

configFileName="config.json"
cacheFileName="cache.json"

class StreamDetective:
    def __init__ (self, dry_run=False, tempDir=None):
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
        self.tagsUrl='https://api.twitch.tv/helix/tags/streams?'
        
        self.gameIdCache={}
        self.gameArtCache={}
        self.tagsCache={}
        self.cooldowns={}
        self.LoadCacheFiles()
        
        self.rateLimitLimit=None
        self.rateLimitRemaining=None
        self.rateLimitReset=None
        self.apiCalls=0
        
        if self.HandleConfigFile():
            print("Created default config.json file")
            exit(0)
        
        self.FetchAllStreams()
        
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
            
    
    def TestConfig(self):
        assert self.config.get('clientId')
        assert self.config.get('accessToken')

        for search in self.config.get('Searches',[]):
            #Must have one but not both
            assert ("GameName" in search) ^ ("UserName" in search), 'testing config for search: ' + repr(search)

        for game in self.config.get('Games',[]):
            assert game.get('GameName'), 'testing config for game: ' + repr(game)
            #assert game.get('DiscordWebhook'), 'testing config for ' + game['GameName']
        
        for streamer in self.config.get('Streamers',[]):
            assert streamer.get('UserName'), 'testing config for streamer: ' + repr(streamer)
        
        for discord in self.config.get('DiscordProfiles', []):
            assert discord.get("ProfileName"), 'testing discord config for: ' + repr(discord)
            assert discord.get("Webhook"), 'testing discord config for: ' + repr(discord)
            assert discord.get("UserName"), 'testing discord config for: ' + repr(discord)

        for twitter in self.config.get('TwitterAccounts', []):
            assert twitter.get("AccountName"), 'testing twitter config for: ' + repr(twitter)

            assert twitter.get("ApiKey"), 'testing twitter config for: ' + repr(twitter)
            assert len(twitter.get("ApiKey")) == 25, 'testing twitter config for: ' + repr(twitter)
            assert '-' not in twitter.get("ApiKey"), 'testing twitter config for: ' + repr(twitter)

            assert twitter.get("ApiKeySecret"), 'testing twitter config for: ' + repr(twitter)
            assert len(twitter.get("ApiKeySecret")) == 50, 'testing twitter config for: ' + repr(twitter)
            assert'-' not in twitter.get("ApiKeySecret"), 'testing twitter config for: ' + repr(twitter)

            assert twitter.get("AccessToken"), 'testing twitter config for: ' + repr(twitter)
            assert len(twitter.get("AccessToken")) == 50, 'testing twitter config for: ' + repr(twitter)
            assert '-' in twitter.get("AccessToken"), 'testing twitter config for: ' + repr(twitter)

            assert twitter.get("AccessTokenSecret"), 'testing twitter config for: ' + repr(twitter)
            assert len(twitter.get("AccessTokenSecret")) == 45, 'testing twitter config for: ' + repr(twitter)
            assert '-' not in twitter.get("AccessTokenSecret"), 'testing twitter config for: ' + repr(twitter)

            assert twitter.get("BearerToken"), 'testing twitter config for: ' + repr(twitter)
            assert len(twitter.get("BearerToken")) > 60, 'testing twitter config for: ' + repr(twitter)
            assert '-' not in twitter.get("BearerToken"), 'testing twitter config for: ' + repr(twitter)
            
        for service in self.config.get('NotificationServices',[]):
            assert service.get("ProfileName"), 'testing notification service for: ' + repr(service)
            assert service.get("Type"), 'testing notification service for: ' + repr(service)
            
            if service.get("Type")=="Twitter":
                assert service.get("ApiKey"), 'testing twitter config for: ' + repr(service)
                assert len(service.get("ApiKey")) == 25, 'testing twitter config for: ' + repr(service)
                assert '-' not in service.get("ApiKey"), 'testing twitter config for: ' + repr(service)

                assert service.get("ApiKeySecret"), 'testing twitter config for: ' + repr(service)
                assert len(service.get("ApiKeySecret")) == 50, 'testing twitter config for: ' + repr(service)
                assert'-' not in service.get("ApiKeySecret"), 'testing twitter config for: ' + repr(service)

                assert service.get("AccessToken"), 'testing twitter config for: ' + repr(service)
                assert len(service.get("AccessToken")) == 50, 'testing twitter config for: ' + repr(service)
                assert '-' in service.get("AccessToken"), 'testing twitter config for: ' + repr(service)

                assert service.get("AccessTokenSecret"), 'testing twitter config for: ' + repr(service)
                assert len(service.get("AccessTokenSecret")) == 45, 'testing twitter config for: ' + repr(service)
                assert '-' not in service.get("AccessTokenSecret"), 'testing twitter config for: ' + repr(service)

                assert service.get("BearerToken"), 'testing twitter config for: ' + repr(service)
                assert len(service.get("BearerToken")) > 60, 'testing twitter config for: ' + repr(service)
                assert '-' not in service.get("BearerToken"), 'testing twitter config for: ' + repr(service)
                
            elif service.get("Type")=="Discord":
                assert service.get("Webhook"), 'testing discord config for: ' + repr(service)
                assert service.get("UserName"), 'testing discord config for: ' + repr(service)
            elif service.get("Type")=="Pushbullet":
                assert service.get("ApiKey"), 'testing pushbullet config for: ' + repr(service)
            
                
            
            
        for i in range(len(self.config.get('IgnoreStreams', []))):
            self.config['IgnoreStreams'][i] = self.config['IgnoreStreams'][i].lower()


    def HandleConfigFile(self):
        configFileFullPath = os.path.join(path,configFileName)
        if os.path.exists(configFileFullPath):
            with open(configFileFullPath, 'r') as f:
                self.config = json.load(f)
            self.TestConfig()
        else:
            print("Writing default config.json file")
            config = {}
            exampleConfigFileFullPath = os.path.join(path,"config.example.json")
            with open(exampleConfigFileFullPath, 'r') as f:
                config = json.load(f)
            
            with open(configFileFullPath, 'w') as f:
                json.dump(config,f, indent=4)

            return True
                
    def HandleSearches(self):
        for search in self.config.get("Searches",[]):
            if "GameName" in search:
                try:
                    self.HandleGame(search)
                except Exception as e:
                    logex(e, 'error in', search)
            elif "UserName" in search:
                try:
                    self.HandleStreamer(search)
                except Exception as e:
                    logex(e, 'error in', search)
                



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
            logex(e, 'request for '+url+' failed: ')
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
                'tags': self.tagsCache,
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
                    self.tagsCache = cache.get('tags',{})
                    self.cooldowns = cache.get('cooldowns',{})
        except Exception as e:
            logex(e, 'error in LoadCacheFile ', cacheFileFullPath)


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
            url += "first=100" #Fetch 100 streams at a time
            
            if cursor!="":
                url+="&after="+cursor
            
            result = None
            result = self.TwitchApiRequest(url)
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
                time.sleep(0.1) #pace yourself a little bit
            
        return allStreams        
    
    def CheckStreamFilter(self, filter, streamer, title, tags, gameName):
        if not filter.keys():
            return True

        if not tags:
            tags = []

        if filter.get('MatchTag'):
            if filter["MatchTag"] not in tags:
                return False
        if filter.get('MatchTagName'):
            if filter["MatchTagName"] not in self.GetTagNames(tags):
                return False
        if filter.get('MatchString'):
            if filter["MatchString"].lower() not in title.lower():
                return False
        if filter.get('DontMatchTag'):
            if filter['DontMatchTag'] in tags:
                return False
        if filter.get('DontMatchString'):
            if filter['DontMatchString'].lower() in title.lower():
                return False
        if filter.get('DontMatchTagName'):
            if filter["DontMatchTagName"] in self.GetTagNames(tags):
                return False
        if filter.get('MatchGameName'):
            if filter["MatchGameName"] != gameName:
                return False
        if filter.get('DontMatchGameName'):
            if filter["DontMatchGameName"] == gameName:
                return False
        if filter.get('DontMatchUser'):
            if filter["DontMatchUser"].lower() == streamer.lower():
                return False

        return True

    def CheckStream(self, entry, streamer, title, tags, gameName):
        trace("Name: ", streamer, title)
        if not entry.get('filters'):
            # return True if the filters array is empty, or the key is missing
            return True
        
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
                logex(e, 'ReadGameCache failed at:', saveLocation, ', with config:', game)
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
                logex(e, 'ReadStreamerCache failed at:', saveLocation, ', with config:', streamer)
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
            tags = stream['tag_ids']
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
            tags = stream['tag_ids']
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
            
            #To remove in time
            self.genWebhookMsgs(self.GetDiscordProfile(game.get("DiscordProfile")), game["GameName"], newStreams, game.get('atUserId'))
            self.genTwitterMsgs(game.get("Twitter",""),newStreams)
            
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

    def genNotifications(self,newStreams,entry):
        notifications = entry.get("Notifications",[])

        for notService in self.config.get("NotificationServices",[]):
            if notService["ProfileName"] in notifications:
                self.handleSingleNotificationService(notService,entry,newStreams)
    
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
    
    def handleSingleNotificationService(self,service,entry,newStreams):
        filteredStreams = self.filterIgnoredStreams(service["ProfileName"],newStreams)
        if self.dry_run:
            print('\nhandleSingleNotificationService dry-run')
            print('service:')
            print(service)
            print('entry:')
            print(entry)
            print("  New Streams: "+str([stream['user_login'] for stream in newStreams]), '\n')
            return
        
        if   service["Type"] == "Pushbullet":
            self.handlePushBulletMsgs(service,filteredStreams)
        elif service["Type"] == "Discord":
            self.handleDiscordMsgs(service,entry,filteredStreams)
        elif service["Type"] == "Twitter":
            self.handleTwitterMsgs(service,filteredStreams)
        else:
            trace("Unknown Notification Service Type: "+service["Type"])
    
    def handleTwitterMsgs(self,service,newStreams):
        for stream in newStreams:
            msg = stream["user_name"] #The capitalized version of the name
            msg+=' is playing '+stream['game_name']+' on Twitch'
            msg+="\n\n"
            msg+= stream["title"]
            link = "\n\nhttps://twitch.tv/"+stream["user_login"]
            if len(msg)+len(link) >= 280:
                msg = msg[:280-len(link)-3] + '...'
            msg+=link
            #print(msg)
            #print("Sending to "+str(profile))
            self.sendTweet(service,msg)

    
    def handlePushBulletMsgs(self,service,newStreams):
        for stream in newStreams:
            title = stream["title"]
            msg = stream["user_login"]+" is playing "+stream["game_name"]
            url = "https://twitch.tv/"+stream["user_login"]
            self.sendPushBulletMessage(service["ApiKey"],title,msg,url=url,emails=service.get("emails"))
    
    def sendPushBulletMessage(self,apiKey,title,body,emails=[None],url=None):
    
        for email in emails:
            data = {"type": "note",
                    "title": title,
                    "body": body,
                    "url":url,
                    "email":email}
            
            headers = {"Accept": "application/json",
                       "Content-Type": "application/json",
                       "User-Agent": "StreamDetective"}
            
            method = "POST"

            url = "https://api.pushbullet.com/v2/pushes"

            jsonData = json.dumps(data)
            
            r = requests.request(method,
                                 url,
                                 data=jsonData,
                                 headers=headers,
                                 auth=HTTPBasicAuth(apiKey, ""))

            r.raise_for_status()
            debug(r.json())


    def GetDiscordProfile(self,profileName):
        if "DiscordProfiles" not in self.config:
            return []
        
        profileNames = []
        profiles = []
        
        if type(profileName) is list:
            profileNames=profileName
        else:
            profileNames.append(profileName)
        
        for profName in profileNames:
            for profile in self.config["DiscordProfiles"]:
                if profile["ProfileName"]==profName:
                    profiles.append(profile)
        return profiles

    def GetTwitterProfile(self,profileName):
        if "TwitterAccounts" not in self.config:
            return []

        profileNames = []
        profiles = []
        
        if type(profileName) is list:
            profileNames=profileName
        else:
            profileNames.append(profileName)
            
        for profName in profileNames:
            for profile in self.config["TwitterAccounts"]:
                name = profile.get("AccountName","")
                if name == profName:
                    profiles.append(profile)
        return profiles

    def sendTweet(self,profile,msg):
        msg = msg[:280]
        api = tweepy.Client( bearer_token=profile["BearerToken"], 
                                    consumer_key=profile["ApiKey"], 
                                    consumer_secret=profile["ApiKeySecret"], 
                                    access_token=profile["AccessToken"], 
                                    access_token_secret=profile["AccessTokenSecret"], 
                                    return_type = requests.Response,
                                    wait_on_rate_limit=True)
        try:
            response = api.create_tweet(text=msg)
            print("Tweet sent")
            debug(response)
        except Exception as e:
            logex(e, "Encountered an issue when attempting to tweet: ", msg)
        

    def genTwitterMsgs(self,twitterProfile,streams):
        profiles = self.GetTwitterProfile(twitterProfile)
        
        for profile in profiles:
            if profile!=None:
                for stream in streams:
                    msg = stream["user_name"] #The capitalized version of the name
                    msg+=' is playing '+stream['game_name']+' on Twitch'
                    msg+="\n\n"
                    msg+= stream["title"]
                    link = "\n\nhttps://twitch.tv/"+stream["user_login"]
                    if len(msg)+len(link) >= 280:
                        msg = msg[:280-len(link)-3] + '...'
                    msg+=link
                    #print(msg)
                    #print("Sending to "+str(profile))
                    self.sendTweet(profile,msg)

    def sendWebhookMsg(self, discordProfile, content, embeds, atUserId, avatarUrl):
        if len(embeds) >= 10:
            embeds = [{"title": str(len(embeds))+' new streams!',"url":'https://twitch.tv',"description": str(len(embeds))+' new streams!'}]
        if atUserId:
            content += ' <@' + str(atUserId) + '>'
        data={
            "username":discordProfile["UserName"],
            "content": content,
            "embeds": embeds
        }
        if avatarUrl:
            data['avatar_url'] = avatarUrl
        debug(data)
        response = requests.post(discordProfile["Webhook"],json=data)
        print("Webhook Response: "+str(response.status_code)+" contents: "+str(response.content))

    def GetUserProfilePicUrl(self,userId):
        userUrl = self.usersUrl+"id="+userId

        result = self.TwitchApiRequest(userUrl)
        if "data" in result and "profile_image_url" in result["data"][0]:
            return result["data"][0]["profile_image_url"]
            
        return ""

    def GetTagNames(self,tags):
        if not tags:
            return []
        tagNames=[]
        tagsUrl = self.tagsUrl
        tagsToFind=0
        
        for tag in tags:
            if tag in self.tagsCache:
                #print("Found tag "+tag+" as "+self.tagsCache[tag])
                tagNames.append(self.tagsCache[tag])
            else:               
                tagsUrl+="tag_id="+tag+"&"
                tagsToFind+=1
                
        if tagsToFind==0:
            return tagNames

        result = self.TwitchApiRequest(tagsUrl)
        #trace(str(result))
        #if "data" in result and "profile_image_url" in result["data"][0]:
        #    return result["data"][0]["profile_image_url"]
        if "data" in result:
            for tagResult in result["data"]:
                #print(tagResult["localization_names"]["en-us"])
                tagName = tagResult["localization_names"]["en-us"]
                self.tagsCache[tagResult["tag_id"]]=tagName
                tagNames.append(tagName)                
        return tagNames
        
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
        

    def buildDiscordMsgs(self, discordProfile, toSend, atUserId):
        content = ''
        embeds = []
        for stream in toSend:
            gameName = stream["game_name"]
            gameArtUrl = ''
            try:
                gameArtUrl = self.getGameBoxArt(gameName,144,192) #144x192 is the value used by Twitch if you open the image in a new tab
            except Exception as e:
                logex(e)

            url="https://twitch.tv/"+stream["user_login"]
            content += url + ' is playing ' + gameName
            #content += ', VOD will probably be here '
            #content += 'https://www.twitch.tv/'+stream["user_login"]+'/videos?filter=archives&sort=time'
            content += '\n'

            streamer = stream["user_name"]

            title = stream["title"]
            title+="\n\n"
            title+='['+stream["user_login"]+' VODs](https://www.twitch.tv/'+stream["user_login"]+'/videos?filter=archives&sort=time)'
                        
            image = self.GetUserProfilePicUrl(stream["user_id"])
            image = {"url":image}
            
            fields = []

            gameField = {}
            gameField["name"]="Game"
            gameField["value"]=gameName
            gameField["inline"]=True
            fields.append(gameField)

            tagsField={}
            tagsField["name"]="Tags"
            tagNames = self.GetTagNames(stream["tag_ids"])
            if tagNames:
                tagsField["value"]=", ".join(tagNames)
            else:
                tagsField["value"]="No Tags"
            tagsField["inline"]=True
            fields.append(tagsField)
            
            embeds.append({"title":streamer,"url":url,"description":title,"image":image,"fields":fields})
            if len(content) >= 1700:
                self.sendWebhookMsg(discordProfile, content, embeds, atUserId,gameArtUrl)
                content = ''
                embeds = []
        
        if content:
            self.sendWebhookMsg(discordProfile, content, embeds, atUserId,gameArtUrl)

    def handleDiscordMsgs(self,profile,entry,newList):
        atUserId = entry.get('atUserId')

        self.buildDiscordMsgs(profile, newList, atUserId)
    

    def genWebhookMsgs(self, discordProfile, gameName, newList, atUserId):
        if not discordProfile:
            return
        
        for profile in discordProfile:
            webhookUrl = profile["Webhook"]
            
            IgnoreStreams = self.config.get('IgnoreStreams', [])
            toSend = []
            for stream in newList:
                if stream["user_login"].lower() in IgnoreStreams:
                    debug(stream["user_login"], 'is in IgnoreStreams')
                    continue
                if self.checkIsOnCooldown(stream, profile["ProfileName"]):
                    continue
                toSend.append(stream)
            
            if toSend:
                self.buildDiscordMsgs(profile, toSend, atUserId)
    
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

def logex(e, *args):
    estr = "".join(traceback.format_exception(BaseException, e, e.__traceback__))
    print("\nERROR: "+estr, *args, '\n')

def fromisoformat(iso):
    # for compatibility with python 3.6
    if not iso:
        return datetime(1970, 1, 1)
    return datetime.strptime(iso, "%Y-%m-%dT%H:%M:%S.%f")

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

setVerbose(verbose)
