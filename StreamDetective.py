from urllib.parse import urlencode
from requests import Session
from requests.adapters import HTTPAdapter
from requests.exceptions import HTTPError, InvalidURL, ConnectionError
import requests
import json
import os.path
import sys
import tempfile

clientId=""
accessToken=""

path = os.path.realpath(os.path.dirname(__file__))
tempDir = os.path.join(tempfile.gettempdir(),"streams")

configFileName="config.json"


#For all I know, this might change at some point?
randoTagId = "2fd30cb8-f2e5-415d-9d42-1316cfa61367"


class StreamDetective:
    def __init__ (self):
        self.session=Session()
        retryAdapter = HTTPAdapter(max_retries=2)
        self.session.mount('https://',retryAdapter)
        self.session.mount('http://',retryAdapter)

        self.streamsUrl='https://api.twitch.tv/helix/streams?game_id='
        self.gameIdUrlBase='https://api.twitch.tv/helix/games?name='


        self.HandleConfigFile()
        self.HandleGames()
        
    def HandleConfigFile(self):
        configFileFullPath = os.path.join(path,configFileName)
        print("Doing this")
        if os.path.exists(configFileFullPath):
            with open(configFileFullPath, 'r') as f:
                self.config = json.load(f)

        else:
            config = {}
            config["clientId"]          = " "
            config["accessToken"]       = " "
            config["GameName"]          = " "
            config["DiscordWebhookUrl"] = " "
            config["DiscordWebhookUser"]= "Stream Detective"

            game = {}
            game["GameName"]=""
            game["StorageFile"]=""
            game["MatchTag"]=""
            game["MatchString"]=""
            game["DiscordWebhook"]=""
            config["Games"] = [game]

            
            
            print("Writing default config file")
            with open(configFileFullPath, 'w') as f:
                json.dump(config,f, indent=4)

            return True

    def HandleGames(self):
        for game in self.config["Games"]:
            self.HandleGame(game)

    def HandleGame(self,game):
        print("Handling "+game["GameName"])
        gameIdUrl = self.gameIdUrlBase+game["GameName"]

        response = self.session.get( gameIdUrl, headers={
            'Client-ID': self.config["clientId"],
            'Authorization': 'Bearer '+self.config["accessToken"],
            'Content-Type': 'application/json'
        })
        try:
            result = json.loads(response.text)
        except:
            result = None

        if (result):
            if "data" in result and len(result["data"])!=0:
                gameId = result["data"][0]["id"]

        if gameId!=None:
            streamsUrl = self.streamsUrl+gameId
            result = None
            response = self.session.get( streamsUrl, headers={
                'Client-ID': self.config["clientId"],
                'Authorization': 'Bearer '+self.config["accessToken"],
                'Content-Type': 'application/json'
            })
            try:
                result = json.loads(response.text)
                #print(response.headers)

            except:
                result = None

            if result:
                #print(result)
                if "data" in result:
                    streamInfo=[]
                    for stream in result["data"]:
                        matched = False
                        streamer = stream['user_login']
                        title = stream['title']
                        tags = stream['tag_ids']
                        print("-------")
                        print("Name: "+streamer)
                        print(title)

                        if game.get("MatchTag","")=="" and game.get("MatchString","")=="":
                            matched=True
                        else:
                            if "MatchTag" in game and game["MatchTag"]!="":
                                if game["MatchTag"] in tags:
                                    matched=True
                            if "MatchString" in game and game["MatchString"]!="":
                                if game["MatchString"].lower() in title.lower():
                                    matched=True

                        if matched:
                            streamInfo.append(stream)
                            
                    print("-------")
                        
        #All stream info now retrieved
        saveLocation = os.path.join(tempDir,game["StorageFile"])
        if os.path.exists(saveLocation):
            f = open(saveLocation,'r')
            streamInfoOld = json.load(f)
            f.close()


            newStreams=self.getNewStreams(streamInfoOld,streamInfo)

            print("New Streams: "+str(newStreams))

            self.genWebhookMsgs(game["DiscordWebhook"],newStreams)
            
            
        if not os.path.exists(tempDir):
            os.makedirs(tempDir)

        f = open(saveLocation,'w')
        json.dump(streamInfo,f)
        f.close()
        
    def isStreamNew(self,old,name):
        found=False
        for stream in old:
            if "user_login" in stream:
                if name.lower()==stream["user_login"].lower():
                    found=True

        return not found
                    

    def getNewStreams(self,old,new):
        newStreams=[]
        for stream in new:
            if "user_login" in stream:
                if self.isStreamNew(old,stream["user_login"]):
                    newStreams.append(stream)
                    print(stream["user_login"]+" is new")

        return newStreams

    def sendWebhookMsg(self,webhookUrl,streamer,title,url):
        data={"username":self.config["DiscordWebhookUser"],"content":url,"embeds":[{"title":streamer,"url":url,"description":title}]}
        response = requests.post(webhookUrl,json=data)
        print("Webhook Response: "+str(response.status_code)+" contents: "+str(response.content))

    def genWebhookMsgs(self,webhookUrl,newList):
        for stream in newList:
            url="https://twitch.tv/"+stream["user_login"]
            self.sendWebhookMsg(webhookUrl,stream["user_name"],stream["title"],url)



sd = StreamDetective()


