from urllib.parse import urlencode
from requests import Session
from requests.adapters import HTTPAdapter
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

clientId=""
accessToken=""

path = os.path.realpath(os.path.dirname(__file__))
path = os.path.dirname(path)
tempDir = os.path.join(tempfile.gettempdir(),"streams")

configFileName="config.json"
cacheFileName="cache.json"

class StreamDetective:
    def __init__ (self):
        print(datetime.now().isoformat()+': StreamDetective starting')
        self.session=Session()
        retryAdapter = HTTPAdapter(max_retries=2)
        self.session.mount('https://',retryAdapter)
        self.session.mount('http://',retryAdapter)

        self.streamsUrl='https://api.twitch.tv/helix/streams?game_id='
        self.usersUrl='https://api.twitch.tv/helix/users?id='
        self.gameIdUrlBase='https://api.twitch.tv/helix/games?name='
        self.tagsUrl='https://api.twitch.tv/helix/tags/streams?'
        
        self.gameIdCache={}
        self.tagsCache={}
        self.cooldowns={}
        self.LoadCacheFiles()
        
        if self.HandleConfigFile():
            print("Created default config.json file")
            exit(0)
        self.HandleGames()
        self.SaveCacheFiles()
        
    def TestConfig(self):
        assert self.config.get('clientId')
        assert self.config.get('accessToken')
        assert self.config.get('Games')
        for game in self.config['Games']:
            assert game.get('GameName'), 'testing config for game: ' + repr(game)
            #assert game.get('DiscordWebhook'), 'testing config for ' + game['GameName']
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

    def HandleGames(self):
        for game in self.config["Games"]:
            try:
                self.HandleGame(game)
            except Exception as e:
                logex(e, 'error in', game)


    def TwitchApiRequest(self, url, headers):
        response = None
        try:
            response = self.session.get( url, headers=headers)
            result = json.loads(response.text)
        except Exception as e:
            print('request for '+url+' failed: ', e)
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
        return result

    def SaveCacheFiles(self):
        cacheFileFullPath = os.path.join(tempDir,cacheFileName)

        with open(cacheFileFullPath, 'w') as f:
            cache = { 'gameIds': self.gameIdCache,
                'tags': self.tagsCache,
                'cooldowns': self.cooldowns
            }
            json.dump(cache,f,indent=4)
        
    def LoadCacheFiles(self):
        cacheFileFullPath = os.path.join(tempDir,cacheFileName)
        try:
            if os.path.exists(cacheFileFullPath):
                with open(cacheFileFullPath, 'r') as f:
                    cache = json.load(f)
                    self.gameIdCache = cache.get('gameIds')
                    self.tagsCache = cache.get('tags')
                    self.cooldowns = cache.get('cooldowns')
        except Exception as e:
            logex(e, 'error in LoadCacheFile ', cacheFileFullPath)


    def AddGameIdToCache(self,gameName,gameId):
        self.gameIdCache[gameName]=gameId

    def GetGameId(self, game):
    
        if game["GameName"] in self.gameIdCache:
            return self.gameIdCache[game["GameName"]]
    
        gameIdUrl = self.gameIdUrlBase+game["GameName"]
        gameId = 0

        headers = {
                'Client-ID': self.config["clientId"],
                'Authorization': 'Bearer '+self.config["accessToken"],
                'Content-Type': 'application/json'
                  }

        result = self.TwitchApiRequest(gameIdUrl,headers)

        if "data" in result and len(result["data"])==1:
            gameId = result["data"][0]["id"]
        else:
            raise Exception(gameIdUrl+" response expected 1 game id: ", result)

        if not gameId:
            raise Exception('gameId is missing')
            
        if gameId:
            self.AddGameIdToCache(game["GameName"],gameId)
            
        return gameId

    def GetAllStreams(self,game,gameId):
        streamsUrl = self.streamsUrl+gameId
        
        allStreams = []
        keepGoing = True
        cursor = ""
        while keepGoing:
            headers = {
                    'Client-ID': self.config["clientId"],
                    'Authorization': 'Bearer '+self.config["accessToken"],
                    'Content-Type': 'application/json'
                      }
                      
            url = streamsUrl+"&first=100" #Fetch 100 streams at a time
            
            if cursor!="":
                url+="&after="+cursor
            
            result = None
            result = self.TwitchApiRequest(url,headers)
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
                time.sleep(0.25) #pace yourself a little bit
            
        return allStreams
        
    
    def CheckStreamFilter(self, filter, streamer, title, tags):
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

        return True

    def CheckStream(self, game, streamer, title, tags):
        #print("-------")
        #print("Name: "+streamer)
        #print(title)
        if not game.get('filters'):
            # return True if the filters array is empty, or the key is missing
            return True
        
        for filter in game['filters']:
            if self.CheckStreamFilter(filter, streamer, title, tags):
                return True
        return False

    def GetGameCachePath(self, gameName):
        gameName = re.sub('[^\w\d ]', '-', gameName)
        return os.path.join(tempDir,gameName)
    
    def ReadGameCache(self, game):
        saveLocation = self.GetGameCachePath(game["GameName"])
        if os.path.exists(saveLocation):
            try:
                f = open(saveLocation,'r')
                streamInfoOld = json.load(f)
                f.close()
                return streamInfoOld
            except Exception as e:
                logex(e, 'ReadGameCache failed at:', saveLocation, ', with config:', game)
        return None

    def HandleGame(self,game):
        print("Handling "+game["GameName"])
        
        gameId = self.GetGameId(game)

        streamInfo = self.ReadGameCache(game)
        hadCache = True
        if streamInfo is None:
            streamInfo = {}
            hadCache = False
        newStreams = []
        
        allStreams = self.GetAllStreams(game,gameId)

        now = datetime.now()

        for stream in allStreams:
            id = stream['id']
            streamer = stream['user_login']
            title = stream['title']
            tags = stream['tag_ids']
            stream['last_seen'] = now.isoformat()
            matched = self.CheckStream(game, streamer, title, tags)
            if matched:
                print("matched "+streamer)
                stream['last_matched'] = now.isoformat()
                if id not in streamInfo:
                    newStreams.append(stream)
            streamInfo[id] = stream
                
        
        # All stream info now retrieved
        if hadCache:
            print("  New Streams: "+str(newStreams))
            self.genWebhookMsgs(self.GetDiscordProfile(game.get("DiscordProfile")), game["GameName"], newStreams, game.get('atUserId'))
            self.genTwitterMsgs(game.get("Twitter",""),newStreams)
            for stream in newStreams:
                id = stream['id']
                streamInfo[id] = stream
        else:
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

        if not os.path.exists(tempDir):
            os.makedirs(tempDir)

        saveLocation = self.GetGameCachePath(game["GameName"])
        f = open(saveLocation,'w')
        json.dump(streamInfo,f)
        f.close()
        print("\n\n")

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
            return None

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
        api = tweepy.Client( bearer_token=profile["BearerToken"], 
                                    consumer_key=profile["ApiKey"], 
                                    consumer_secret=profile["ApiKeySecret"], 
                                    access_token=profile["AccessToken"], 
                                    access_token_secret=profile["AccessTokenSecret"], 
                                    return_type = requests.Response,
                                    wait_on_rate_limit=True)
        try:
            msg = msg[:280]
            response = api.create_tweet(text=msg)
            print("Tweet sent")
        except Exception as e:
            print("Encountered an issue when attempting to tweet: "+str(e)+" "+str(e.args))
        

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

    def sendWebhookMsg(self, discordProfile, content, embeds, atUserId):
        if len(embeds) >= 10:
            embeds = [{"title": str(len(embeds))+' new streams!',"url":'https://twitch.tv',"description": str(len(embeds))+' new streams!'}]
        if atUserId:
            content += ' <@' + str(atUserId) + '>'
        data={
            "username":discordProfile["UserName"],
            "content": content,
            "embeds": embeds
        }
        print(data)
        response = requests.post(discordProfile["Webhook"],json=data)
        print("Webhook Response: "+str(response.status_code)+" contents: "+str(response.content))

    def GetUserProfilePicUrl(self,userId):
        userUrl = self.usersUrl+userId

        headers = {
                'Client-ID': self.config["clientId"],
                'Authorization': 'Bearer '+self.config["accessToken"],
                'Content-Type': 'application/json'
                  }

        result = self.TwitchApiRequest(userUrl,headers)
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

        headers = {
                'Client-ID': self.config["clientId"],
                'Authorization': 'Bearer '+self.config["accessToken"],
                'Content-Type': 'application/json'
                  }

        result = self.TwitchApiRequest(tagsUrl,headers)
        #print(str(result))
        #if "data" in result and "profile_image_url" in result["data"][0]:
        #    return result["data"][0]["profile_image_url"]
        if "data" in result:
            for tagResult in result["data"]:
                #print(tagResult["localization_names"]["en-us"])
                tagName = tagResult["localization_names"]["en-us"]
                self.tagsCache[tagResult["tag_id"]]=tagName
                tagNames.append(tagName)                
        return tagNames
        

    def buildWebhookMsgs(self, discordProfile, gameName, toSend, atUserId):
        content = ''
        embeds = []
        for stream in toSend:
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
            tagsField["value"]=", ".join(self.GetTagNames(stream["tag_ids"]))
            tagsField["inline"]=True
            fields.append(tagsField)
            
            embeds.append({"title":streamer,"url":url,"description":title,"image":image,"fields":fields})
            if len(content) >= 1700:
                self.sendWebhookMsg(discordProfile, content, embeds, atUserId)
                content = ''
                embeds = []
        
        if content:
            self.sendWebhookMsg(discordProfile, content, embeds, atUserId)

    def genWebhookMsgs(self, discordProfile, gameName, newList, atUserId):
        if not discordProfile:
            return
        
        for profile in discordProfile:
            webhookUrl = profile["Webhook"]
            
            IgnoreStreams = self.config.get('IgnoreStreams', [])
            toSend = []
            for stream in newList:
                if stream["user_login"].lower() in IgnoreStreams:
                    continue
                if self.checkIsOnCooldown(stream, webhookUrl):
                    continue
                toSend.append(stream)
            
            if toSend:
                self.buildWebhookMsgs(profile, gameName, toSend, atUserId)
    
    def checkIsOnCooldown(self, stream, webhookUrl):
        user = stream["user_login"].lower()
        key = user + '-' + webhookUrl
        now = datetime.now()
        cooldown = self.cooldowns.get(key)
        if not cooldown:
            self.cooldowns[key] = { 'last_notified': now.isoformat() }
            return False
        last_notified = cooldown['last_notified']
        last_notified = fromisoformat(last_notified)
        if (now - last_notified).total_seconds() < self.config.get('CooldownSeconds',0):
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
