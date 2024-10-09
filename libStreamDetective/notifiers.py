
from libStreamDetective import *
from libStreamDetective.twitch import TwitchApi
from libStreamDetective.util import *
import json
from requests.auth import HTTPBasicAuth
import requests
import tweepy
from mastodon import Mastodon
import random

debug = print
trace = print

class Notifier():
    # override this in subclasses
    def handleMsgs(self, entry, newStreams):
        for stream in newStreams:
            print(self.ProfileName, ':', stream["title"])

    def __init__(self, config, dry_run):
        self.config = config
        self.ProfileName = config['ProfileName']
        self.dry_run = dry_run
        self.MessagesSent = 0
        self.ErrorsSent = 0
    

    def sendError(self, errMsg):
        raise RuntimeError(errMsg)

    def handleSingleNotificationService(self, notifierData, entry, newStreams):
        if self.dry_run:
            print('\nhandleSingleNotificationService dry-run')
            print('service:')
            print(self)
            print('entry:')
            print(entry)
            print("  New Streams: "+str([stream['user_login'] for stream in newStreams]), '\n')
            return
        
        if notifierData and notifierData.get('chance', 100) < random.randint(1, 100):
            return
        
        if newStreams:
            self.handleMsgs(entry, newStreams)
            self.MessagesSent += 1


    def handleErrorSingleNotificationService(self, errMsg):
        self.sendError(errMsg)
        self.ErrorsSent += 1
    
    
    def GetUserProfilePicUrl(self,userId):
        userUrl = TwitchApi.usersUrl+"id="+userId

        result = TwitchApi.Request(userUrl)
        if "data" in result and "profile_image_url" in result["data"][0]:
            return result["data"][0]["profile_image_url"]
            
        return ""
        



class PushbulletNotifier(Notifier):
    def handleMsgs(self, entry, newStreams):
        titleOverride=entry.get("TitleOverride",None)
        for stream in newStreams:
            title = stream["title"]
            if titleOverride:
                msg = stream["user_login"]+" is playing "+titleOverride
            else:
                msg = stream["user_login"]+" is playing "+stream["game_name"]
            url = "https://twitch.tv/"+stream["user_login"]
            self.sendPushBulletMessage(self.config["ApiKey"], title, msg, url=url, emails=self.config.get("emails"))
    
    
    def sendError(self, errMsg):
        self.sendPushBulletMessage(self.config["ApiKey"], "Stream Detective Error", errMsg)
    

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




class DiscordNotifier(Notifier):
    def handleMsgs(self, entry, newList):
        atUserId = entry.get('atUserId')
        titleOverride=entry.get('TitleOverride',None)
        gameArtOverride=entry.get('GameArtOverride',None)
        customMessage=entry.get('CustomDiscordMessage')

        self.buildDiscordMsgs(self.config, newList, atUserId, titleOverride, gameArtOverride, customMessage)

    
    def sendError(self, errMsg):
        self.sendWebhookMsg(self.config, errMsg, [], [], [])

    
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

    
    def buildDiscordMsgs(self, discordProfile, toSend, atUserId, titleOverride, gameArtOverride, customMessage):
        content = ''
        embeds = []
        if customMessage:
            content += customMessage + '\n'
        for stream in toSend:
        
            if titleOverride:
                gameName = titleOverride
            else:
                gameName = stream["game_name"]
                       
            gameArtUrl = ''
            try:
                gameArtName = gameName
                if gameArtOverride:
                    gameArtName = gameArtOverride
                gameArtUrl = TwitchApi.getGameBoxArt(gameArtName,144,192) #144x192 is the value used by Twitch if you open the image in a new tab
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
            tagNames = stream["tags"]
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
                if customMessage:
                    content += customMessage + '\n'
        
        if content:
            self.sendWebhookMsg(discordProfile, content, embeds, atUserId,gameArtUrl)



class MastodonNotifier(Notifier):
    def handleMsgs(self, entry, newStreams):
        titleOverride=entry.get("TitleOverride",None)
        footerText=entry.get("MastoFooter")
        for stream in newStreams:
            msg = stream["user_name"] #The capitalized version of the name
            if titleOverride:
                msg+=' is playing '+titleOverride+' on Twitch'
            else:
                msg+=' is playing '+stream['game_name']+' on Twitch'
            msg+="\n\n"
            msg+= stream["title"].replace('#', '*') # don't let streamers dump hashtags on our bot!
            after = "\n\nhttps://twitch.tv/"+stream["user_login"]
            if footerText:
                after += '\n\n' + footerText + ' #StreamDetective'
            else:
                after += "\n\n#StreamDetective"
            
            if len(msg)+len(after) >= 500:
                msg = msg[:500-len(after)-3] + '...'
            msg+=after
            #print(msg)
            #print("Sending to "+str(profile))
            self.sendToot(self.config, msg)

    
    def sendError(self, errMsg):
        self.sendToot(self.config, errMsg, raise_exc=False)


    def sendToot(self,profile,msg,raise_exc=True):
        msg = msg[:500]

        api = Mastodon(client_id=profile["ClientKey"],
                       client_secret=profile["ClientSecret"],
                       access_token=profile["AccessToken"],
                       api_base_url=profile["BaseURL"])

        try:
            response = api.status_post(msg)
            print("Toot sent")
            debug(response)
        except Exception as e:
            if raise_exc:
                logex(e, "Encountered an issue when attempting to toot: ", msg)





class TwitterNotifier(Notifier):
    def handleMsgs(self, entry, newStreams):
        titleOverride=entry.get("TitleOverride",None)
        for stream in newStreams:
            msg = stream["user_name"] #The capitalized version of the name
            if titleOverride:
                msg+=' is playing '+titleOverride+' on Twitch'
            else:
                msg+=' is playing '+stream['game_name']+' on Twitch'
            msg+="\n\n"
            msg+= stream["title"]
            after = "\n\nhttps://twitch.tv/"+stream["user_login"]
            after += "\n\n#StreamDetective"
            if len(msg)+len(after) >= 280:
                msg = msg[:280-len(after)-3] + '...'
            msg+=after
            #print(msg)
            #print("Sending to "+str(profile))
            self.sendTweet(msg)


    def sendError(self, errMsg):
        self.sendTweet(self.config, errMsg, raise_exc=False)

    
    def sendTweet(self, msg, raise_exc=True):
        profile = self.config
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
            if raise_exc:
                logex(e, "Encountered an issue when attempting to tweet: ", msg)




def CreateNotifier(config, dry_run) -> Notifier:
    newClass = Notifier
    type = config["Type"]

    if   type == "Pushbullet":
        newClass = PushbulletNotifier
    elif type == "Discord":
        newClass = DiscordNotifier
    elif type == "Twitter":
        newClass = TwitterNotifier
    elif type == "Mastodon":
        newClass = MastodonNotifier
    else:
        raise RuntimeError("unknown NotificationService type "+type, config)
    return newClass(config, dry_run)
