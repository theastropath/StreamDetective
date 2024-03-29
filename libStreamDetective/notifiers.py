
from libStreamDetective import *
from libStreamDetective.libStreamDetective import *

debug = print
trace = print

class Notifier:
    usersUrl='https://api.twitch.tv/helix/users?'

    def __init__(self, config, parent):
        self.config = config
        self.ProfileName = config['ProfileName']
        self.parent = parent
        self.dry_run = parent.dry_run
        self.MessagesSent = 0
        self.ErrorsSent = 0
    

    def sendError(self, errMsg):
        raise RuntimeError(errMsg)

    def handleSingleNotificationService(self, entry, newStreams):
        filteredStreams = self.parent.filterIgnoredStreams(self.ProfileName, newStreams)
        if self.dry_run:
            print('\nhandleSingleNotificationService dry-run')
            print('service:')
            print(self)
            print('entry:')
            print(entry)
            print("  New Streams: "+str([stream['user_login'] for stream in newStreams]), '\n')
            return
        
        if filteredStreams:
            self.handleMsgs(entry, filteredStreams)
            self.MessagesSent += 1


    def handleErrorSingleNotificationService(self, errMsg):
        self.sendError(errMsg)
        self.ErrorsSent += 1
    
    
    def GetUserProfilePicUrl(self,userId):
        userUrl = self.usersUrl+"id="+userId

        result = self.parent.TwitchApiRequest(userUrl)
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
        customMessage=entry.get('CustomDiscordMessage')

        self.buildDiscordMsgs(self.config, newList, atUserId, titleOverride, customMessage)

    
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

    
    def buildDiscordMsgs(self, discordProfile, toSend, atUserId, titleOverride, customMessage):
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
                gameArtUrl = self.parent.getGameBoxArt(gameName,144,192) #144x192 is the value used by Twitch if you open the image in a new tab
            except Exception as e:
                logex(self.parent, e)

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
                logex(self.parent, e, "Encountered an issue when attempting to toot: ", msg)





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
                logex(self.parent, e, "Encountered an issue when attempting to tweet: ", msg)




def CreateNotifier(config, parent) -> Notifier:
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
    return newClass(config, parent)
