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

clientId=""
accessToken=""

path = os.path.realpath(os.path.dirname(__file__))
tempDir = os.path.join(tempfile.gettempdir(),"streams")

configFileName="config.json"

class StreamDetective:
    def __init__ (self):
        self.session=Session()
        retryAdapter = HTTPAdapter(max_retries=2)
        self.session.mount('https://',retryAdapter)
        self.session.mount('http://',retryAdapter)

        self.streamsUrl='https://api.twitch.tv/helix/streams?game_id='
        self.gameIdUrlBase='https://api.twitch.tv/helix/games?name='

        if self.HandleConfigFile():
            print("Created default config.json file")
            exit(0)
        self.HandleGames()
        
    def HandleConfigFile(self):
        configFileFullPath = os.path.join(path,configFileName)
        print("Doing this")
        if os.path.exists(configFileFullPath):
            with open(configFileFullPath, 'r') as f:
                self.config = json.load(f)

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


    def TwitchApiRequest(self, url):
        response = None
        try:
            response = self.session.get( url, headers={
                'Client-ID': self.config["clientId"],
                'Authorization': 'Bearer '+self.config["accessToken"],
                'Content-Type': 'application/json'
            })
            result = json.loads(response.text)
        except Exception as e:
            print('request for '+url+' failed: ', e)
            raise

        if not result:
            print('request for '+url+' failed')
            raise Exception('request failed')
        if 'status' in result and result['status'] != 200:
            print('request for '+url+' failed: ', result)
            raise Exception('request failed', result)
        return result


    def CheckStream(self, filter, streamer, title, tags):
        #print("-------")
        #print("Name: "+streamer)
        #print(title)

        if filter.get("MatchTag","")=="" and filter.get("MatchString","")=="":
            return True

        if "MatchTag" in filter and filter["MatchTag"]!="":
            if filter["MatchTag"] in tags:
                return True
        if "MatchString" in filter and filter["MatchString"]!="":
            if filter["MatchString"].lower() in title.lower():
                return True
        return False

    def ReadGameCache(self, game):
        saveLocation = os.path.join(tempDir,game["GameName"])
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
        gameIdUrl = self.gameIdUrlBase+game["GameName"]

        # TODO: cache gameIds so we can continue if this fails, or even skip this API call
        result = self.TwitchApiRequest(gameIdUrl)

        if "data" in result and len(result["data"])==1:
            gameId = result["data"][0]["id"]
        else:
            raise Exception(gameIdUrl+" response expected 1 game id: ", result)

        if not gameId:
            raise Exception('gameId is missing')

        streamInfo = self.ReadGameCache(game)
        hadCache = True
        if streamInfo is None:
            streamInfo = {}
            hadCache = False
        newStreams = []
        
        streamsUrl = self.streamsUrl+gameId
        result = self.TwitchApiRequest(streamsUrl)
        now = datetime.now()

        if result and 'data' in result:
            for stream in result["data"]:
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
                    
            print("-------")
        
        # All stream info now retrieved
        if hadCache:
            print("New Streams: "+str(newStreams))
            self.genWebhookMsgs(game["DiscordWebhook"], game["GameName"], newStreams)
            for stream in newStreams:
                id = stream['id']
                streamInfo[id] = stream
        else:
            newStreams = []
            print("Old streams cache not found, creating it now")
            
        # cleanup old entries in cache
        for key, val in streamInfo.items():
            last_seen = datetime.fromisoformat(val['last_seen'])
            if (now - last_seen).total_seconds() > (3600*24):
                del streamInfo[key]

        if not os.path.exists(tempDir):
            os.makedirs(tempDir)

        saveLocation = os.path.join(tempDir,game["GameName"])
        f = open(saveLocation,'w')
        json.dump(streamInfo,f)
        f.close()


    def sendWebhookMsg(self, webhookUrl, gameName, streamer, title, url):
        data={
            "username":self.config["DiscordWebhookUser"],
            "content":url + ' is playing ' + gameName,
            "embeds":[{"title":streamer,"url":url,"description":title}]
        }
        response = requests.post(webhookUrl,json=data)
        print("Webhook Response: "+str(response.status_code)+" contents: "+str(response.content))

    def genWebhookMsgs(self, webhookUrl, gameName, newList):
        if not webhookUrl:
            return
        IgnoreStreams = self.config.get('IgnoreStreams', [])
        for stream in newList:
            if stream["user_login"] in IgnoreStreams:
                continue
            last_notified = datetime.fromisoformat(stream['last_notified'])
            now = datetime.now()
            # update this timestamp so we don't just notify again later?
            # this whole thing might be obsolete since we use the id of the stream instead of the streamer username?
            # cooldown should probably be per streamer not stream id
            stream['last_notified'] = now.isoformat()
            if (now - last_notified).total_seconds() < self.config['CooldownSeconds']:
                continue
            url="https://twitch.tv/"+stream["user_login"]
            self.sendWebhookMsg(webhookUrl, gameName, stream["user_name"],stream["title"],url)

def logex(e, *args):
    estr = "".join(traceback.format_exception(BaseException, e, e.__traceback__))
    print("\nERROR: "+estr, *args, '\n')

sd = StreamDetective()
