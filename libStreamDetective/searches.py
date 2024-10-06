from datetime import datetime
import os
from libStreamDetective.util import *

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

    streamInfo = self.ReadGameCache(game)
    hadCache = True
    if streamInfo is None:
        streamInfo = {}
        hadCache = False
    newStreams = []
    
    allStreams = self.GetAllGameStreams(game["GameName"])

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
