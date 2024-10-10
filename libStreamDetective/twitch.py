import time

import urllib.parse
from libStreamDetective import db
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

    
    def FetchAllStreams(self, gameNames:set, tagsets:dict, streamers:set):
        #print("All Games: "+str(gameNames))
        #print("All Streamers: "+str(streamers))
        fetchedGames = {}
        fetchedTags = {}
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
                if stream not in fetchedGames[gameName]:
                    fetchedGames[gameName].append(stream)
                user = stream["user_login"].lower()
                fetchedStreamers[user] = stream

        fetched = None # just in case
        if tagsets:
            url = TwitchApi.streamsUrl
            fetched = self.GetAllStreams(url)
        for (k,v) in tagsets.items():
            if k not in fetchedTags:
                fetchedTags[k] = []
            for stream in fetched:
                user = stream["user_login"].lower()
                fetchedStreamers[user] = stream
                if stream in fetchedTags[k]:
                    continue
                if self.MatchAnyTag(v, stream['tags']):
                    fetchedTags[k].append(stream)
            
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
        return (fetchedGames, fetchedTags, fetchedStreamers)


    @staticmethod
    def MatchAllTags(desiredTags, actualTags):
        try:
            for desiredTag in desiredTags:
                matched = False
                for actualTag in actualTags:
                    if desiredTag.lower() == actualTag.lower():
                        matched = True
                        break
                if not matched:
                    return False
            return True
        except:
            return False
        
    @staticmethod
    def MatchAnyTag(desiredTags, actualTags):
        try:
            for desiredTag in desiredTags:
                for actualTag in actualTags:
                    if desiredTag.lower() == actualTag.lower():
                        return True
            return False
        except:
            return False
    
    def GetAllStreams(self, lookupUrl, maxPages=100):
        allStreams = []
        cursor = ""
        resume_page = 0
        res = db.fetchone('SELECT cursor, page FROM queries WHERE baseurl=? AND updated>? AND page<100000', (lookupUrl,unixtime()-3600))
        if res:
            cursor = res[0]
            resume_page = res[1]
            debug('resuming cursor', cursor, resume_page)
        for page in range(maxPages):
            url = lookupUrl
            if not lookupUrl.endswith('&'):
                url += '&'
            url += "first=100" # Fetch 100 streams at a time
            
            if cursor!="":
                url+="&after="+cursor

            result = TwitchApi.Request(url)
            
            for stream in result['data']:
                allStreams.append(stream)
            
            # Twitch API doesn't always return full pages, so we need to load the next page no matter what
            if "pagination" in result and "cursor" in result["pagination"]:
                cursor = result["pagination"]["cursor"]
                time.sleep(0.01) # pace yourself a little bit
            else:
                cursor = ""
                break
        
        if cursor:
            debug('pausing on cursor', cursor)
            db.upsert('queries', dict(baseurl=lookupUrl, cursor=cursor, page=page+resume_page, updated=unixtime()))
        else:
            if resume_page:
                print('finished pass through', lookupUrl, 'after', page+resume_page, 'pages')
            db.exec('DELETE FROM queries WHERE baseurl=?', (lookupUrl,))

        return allStreams
    

    def end(self):
        global rateLimitLimit, rateLimitReset, rateLimitRemaining, apiCalls
        if rateLimitLimit is not None and rateLimitReset is not None:
            #Output rate limit info
            print("Rate Limit: "+str(rateLimitRemaining)+"/"+str(rateLimitLimit)+" - Resets at "+datetime.fromtimestamp(rateLimitReset).strftime('%c'))
        print("Number of API Calls: "+str(apiCalls))


class TwitchApi:
    streamsUrl='https://api.twitch.tv/helix/streams?type=live&'
    usersUrl='https://api.twitch.tv/helix/users?'
    queryUrl='https://api.twitch.tv/helix/search/channels?' # doesn't even work https://github.com/theastropath/StreamDetective/issues/34#issuecomment-2403683986
    gameIdCache={}
    gameArtCache={}

    @staticmethod
    def GetGameArt(gameName: str) -> str:
        gameId = TwitchApi.GetGameId(gameName)
        return "https://static-cdn.jtvnw.net/ttv-boxart/" + gameId + "_IGDB-144x192.jpg" # we use these for the Discord profile pic, Twitch shows them at 285x380
    
    @staticmethod
    def GetStreamerThumbnail(streamer: str) -> str:
        return "https://static-cdn.jtvnw.net/previews-ttv/live_user_" + streamer + "-320x180.jpg"

    @staticmethod
    def GetGameId(gameName):
        if gameName in TwitchApi.gameIdCache:
            return TwitchApi.gameIdCache[gameName]
        
        res = db.fetchone('SELECT id FROM games where name=?', (gameName,))
        if res:
            TwitchApi.gameIdCache[gameName] = res[0]
            return res[0]

        return TwitchApi.fetchGameInfo(gameName)
    

    @staticmethod
    def fetchGameInfo(gameName):
        gameUrl = "https://api.twitch.tv/helix/games?name="+gameName
        
        result = TwitchApi.Request(gameUrl)
        if result.get('data') and result["data"][0].get('id'):
            gameId = result["data"][0]["id"]
            TwitchApi.gameIdCache[gameName]=gameId
            now = unixtime()
            db.exec('INSERT INTO games(name, id, updated) VALUES(?,?,?)', (gameName, gameId, now))
            return gameId
        raise Exception('fetchGameInfo ' + gameUrl + ' failed')


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
