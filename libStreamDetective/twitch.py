import time
from libStreamDetective.util import *
from requests import Session
from requests.adapters import HTTPAdapter
import json

clientId=None
accessToken=None
session=Session()
retryAdapter = HTTPAdapter(max_retries=2)
session.mount('https://',retryAdapter)
session.mount('http://',retryAdapter)

rateLimitLimit=None
rateLimitRemaining=None
rateLimitReset=None
apiCalls=0

class Twitch:
    def __init__(self, config):
        global clientId, accessToken
        clientId = config['clientId']
        accessToken = config['accessToken']

    
    def FetchAllStreams(self, gameNames:set, streamers:set):
        #print("All Games: "+str(gameNames))
        #print("All Streamers: "+str(streamers))
        fetchedGames = {}
        fetchedStreamers = {}
        
        # TODO: This should be extended to handle more than 100 unique games
        if gameNames:
            allGamesUrl = TwitchApi.streamsUrl
            for game in gameNames:
                gameId = TwitchApi.GetGameId(game)
                allGamesUrl += "game_id="+gameId+"&"
            #print("All games: "+allGamesUrl)
            fetched = self.GetAllStreams(allGamesUrl)
            for stream in fetched:
                gameName = stream["game_name"].lower()
                if gameName not in fetchedGames:
                    fetchedGames[gameName] = []
                fetchedGames[gameName].append(stream)
                user = stream["user_login"].lower()
                fetchedStreamers[user] = stream
            
        # TODO: This should be extended to handle more than 100 unique streamers
        if streamers:
            allStreamersUrl = TwitchApi.streamsUrl
            for streamer in streamers:
                if streamer.lower() not in fetchedStreamers: # don't need to fetch them if we found them above
                    allStreamersUrl += "user_login="+streamer+"&"
            fetched = self.GetAllStreams(allStreamersUrl)
            for stream in fetched:
                user = stream["user_login"].lower()
                fetchedStreamers[user] = stream

        self.end()
        return (fetchedGames, fetchedStreamers)

    
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
            result = TwitchApi.Request(url)
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
    

    def end(self):
        global rateLimitLimit, rateLimitReset, rateLimitRemaining, apiCalls
        if rateLimitLimit is not None and rateLimitReset is not None:
            #Output rate limit info
            print("Rate Limit: "+str(rateLimitRemaining)+"/"+str(rateLimitLimit)+" - Resets at "+datetime.fromtimestamp(rateLimitReset).strftime('%c'))
        print("Number of API Calls: "+str(apiCalls))


class TwitchApi:
    streamsUrl='https://api.twitch.tv/helix/streams?'
    usersUrl='https://api.twitch.tv/helix/users?'
    gameIdCache={}
    gameArtCache={}

    @staticmethod
    def GetGameId(gameName):
        if gameName in TwitchApi.gameIdCache:
            return TwitchApi.gameIdCache[gameName]

        gameIdUrlBase='https://api.twitch.tv/helix/games?'
        gameIdUrl = gameIdUrlBase+"name="+gameName
        gameId = 0
        boxArt = ""

        result = TwitchApi.Request(gameIdUrl)

        if "data" in result and len(result["data"])==1:
            gameId = result["data"][0]["id"]
            boxArt = result["data"][0]["box_art_url"].replace("{width}","144").replace("{height}","192")
        else:
            raise Exception(gameIdUrl+" response expected 1 game id: ", result)

        if not gameId:
            raise Exception('gameId is missing')
            
        if gameId:
            TwitchApi.AddGameIdToCache(gameName,gameId)
            
        if boxArt:
            TwitchApi.AddGameArtToCache(gameName,boxArt)
            
        return gameId

    @staticmethod
    def getGameBoxArt(gameName,width,height):
        if gameName in TwitchApi.gameArtCache:
            return TwitchApi.gameArtCache[gameName]

        gameUrl = "https://api.twitch.tv/helix/games?name="+gameName
        
        result = TwitchApi.Request(gameUrl)
        if result.get('data') and result["data"][0].get('box_art_url'):
            url = result["data"][0]["box_art_url"]
            url = url.replace("{width}",str(width)).replace("{height}",str(height))
            TwitchApi.AddGameArtToCache(gameName,url)
            return url
        return ""

    @staticmethod
    def AddGameIdToCache(gameName,gameId):
        TwitchApi.gameIdCache[gameName]=gameId

    @staticmethod
    def AddGameArtToCache(gameName,artUrl):
        TwitchApi.gameArtCache[gameName]=artUrl

    @staticmethod
    def Request(url, headers={}):
        global clientId, accessToken, session, apiCalls, rateLimitRemaining, rateLimitLimit, rateLimitRemaining, rateLimitReset
        debug('TwitchApiRequest', url, headers)
        response = None

        if apiCalls > 200:
            raise Exception('too many Twitch API calls', apiCalls)
        if rateLimitRemaining is not None and rateLimitRemaining < 10:
            raise Exception('rate limit remaining is too low', rateLimitRemaining)

        try:
            headers = {
                'Client-ID': clientId,
                'Authorization': 'Bearer '+accessToken,
                'Content-Type': 'application/json',
                **headers
            }
            response = session.get(url, headers=headers)
            apiCalls+=1
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
            rateLimitLimit = int(response.headers["Ratelimit-Limit"])
            debug('TwitchApiRequest','Ratelimit-Remaining', response.headers["Ratelimit-Remaining"])
            rateLimitRemaining = int(response.headers["Ratelimit-Remaining"])
            debug('TwitchApiRequest','Ratelimit-Reset', response.headers["Ratelimit-Reset"])
            rateLimitReset = int(response.headers["Ratelimit-Reset"])
            
        debug('TwitchApiRequest', 'results:', len(result.get('data', [])))
        return result
