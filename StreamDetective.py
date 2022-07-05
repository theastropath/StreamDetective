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

session=Session()

allInfoSaveFile="AllStreamsInfo"
allInfoSaveLocation=os.path.join(tempDir,allInfoSaveFile)
randoInfoSaveFile="RandoStreamsInfo"
randoInfoSaveLocation=os.path.join(tempDir,randoInfoSaveFile)

configFileName="config.json"

streamsUrl='https://api.twitch.tv/helix/streams?game_id='
gameIdUrl=''
gameIdUrlBase='https://api.twitch.tv/helix/games?name='

gameId = None

#For all I know, this might change at some point?
randoTagId = "2fd30cb8-f2e5-415d-9d42-1316cfa61367"

allStreamInfo=[]
randoStreamInfo=[]

oldStreamInfo=[]
oldRandoInfo=[]

webhookUserName = "Stream Detective"
webhookUrl = ""


retryAdapter = HTTPAdapter(max_retries=2)
session.mount('https://',retryAdapter)
session.mount('http://',retryAdapter)


def isStreamNew(old,name):
    found=False
    for stream in old:
        if "user_login" in stream:
            if name.lower()==stream["user_login"].lower():
                found=True

    return not found
                

def getNewStreams(old,new):
    newStreams=[]
    for stream in new:
        if "user_login" in stream:
            if isStreamNew(old,stream["user_login"]):
                newStreams.append(stream)
                print(stream["user_login"]+" is new")

    return newStreams

def sendWebhookMsg(streamer,title,url):
    data={"username":webhookUserName,"content":url,"embeds":[{"title":streamer,"url":url,"description":title}]}
    response = requests.post(webhookUrl,json=data)
    print("Webhook Response: "+str(response.status_code)+" contents: "+str(response.content))

def genWebhookMsgs(newList):
    for stream in newList:
        url="https://twitch.tv/"+stream["user_login"]
        sendWebhookMsg(stream["user_name"],stream["title"],url)

def HandleConfigFile():
    global gameIdUrl,clientId,accessToken,webhookUrl,webhookUserName

    configFileFullPath = os.path.join(path,configFileName)
    
    if os.path.exists(configFileFullPath):
        with open(configFileFullPath, 'r') as f:
            config = json.load(f)

        gameIdUrl = gameIdUrlBase+config["GameName"]
        clientId = config["clientId"]
        accessToken = config["accessToken"]
        webhookUrl = config["DiscordWebhookUrl"]
        webhookUserName = config["DiscordWebhookUser"]
        return False
    else:
        config = {}
        config["clientId"]          = " "
        config["accessToken"]       = " "
        config["GameName"]          = " "
        config["DiscordWebhookUrl"] = " "
        config["DiscordWebhookUser"]= "Stream Detective"
        print("Writing default config file")
        with open(configFileFullPath, 'w') as f:
            json.dump(config,f, indent=4)

        return True


        

if HandleConfigFile():
    sys.exit(0)

response = session.get( gameIdUrl, headers={
    'Client-ID': clientId,
    'Authorization': 'Bearer '+accessToken,
    'Content-Type': 'application/json'
})
try:
    result = json.loads(response.text)
    #print(response.headers)
except:
    result = None

if (result):
    #print(result)
    if "data" in result and len(result["data"])!=0:
        gameId = result["data"][0]["id"]
        #print("Deus Ex ID: "+str(gameId))

if gameId!=None:
    streamsUrl+=gameId
    result = None
    response = session.get( streamsUrl, headers={
        'Client-ID': clientId,
        'Authorization': 'Bearer '+accessToken,
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
            allStreamInfo=result["data"]
            for stream in result["data"]:
                isRando = False
                streamer = stream['user_login']
                title = stream['title']
                tags = stream['tag_ids']
                print("-------")
                print("Name: "+streamer)
                print(title)
                if randoTagId in tags:
                    print("Has Randomizer tag set!")
                    isRando = True
                if "rando" in title.lower():
                    print("Title suggests it might be the rando")
                    isRando = True

                if isRando:
                    randoStreamInfo.append(stream)
                    
            print("-------")
                
#All stream info now retrieved
    
if os.path.exists(allInfoSaveLocation) and os.path.exists(randoInfoSaveLocation):
    f = open(allInfoSaveLocation,'r')
    allInfoOld = json.load(f)
    f.close()

    f = open(randoInfoSaveLocation,'r')
    randoInfoOld = json.load(f)
    f.close()



    newAllStreams=getNewStreams(allInfoOld,allStreamInfo)
    newRandoStreams=getNewStreams(randoInfoOld,randoStreamInfo)

    print("New Streams: "+str(newAllStreams))
    print("New Rando Streams: "+str(newRandoStreams))

    genWebhookMsgs(newRandoStreams)
    
    
if not os.path.exists(tempDir):
    os.makedirs(tempDir)

f = open(allInfoSaveLocation,'w')
json.dump(allStreamInfo,f)
f.close()

f = open(randoInfoSaveLocation,'w')
json.dump(randoStreamInfo,f)
f.close()




