from datetime import datetime
import os
from libStreamDetective.util import *


def HandleFilters(self, search, allStreams):
    newStreams = []
    now = datetime.now()
    searchAll = 'SearchAll' in search
    searchTags = search.get('SearchTags')

    for stream in allStreams:
        streamer = stream['user_login']
        title = stream['title']
        tags = stream['tags']
        stream['last_seen'] = now.isoformat()
        if searchTags and not MatchAnyTag(searchTags, tags): # for now, this makes it easier to require different combos of tags, as seen in DosSpeedruns.json
            continue
        matched = self.CheckStream(search, streamer, title, tags, stream["game_name"])
        if matched:
            debug("matched "+streamer)
            stream['last_matched'] = now.isoformat()
            newStreams.append(stream)
        elif not searchAll:
            trace('didn\'t match', streamer)
            
    # All stream info now retrieved
    if newStreams:
        print("   Matched Streams:", [stream['user_login'] for stream in newStreams])
        self.genNotifications(newStreams, search)
    
    debug("\n\n")
    return newStreams


def MatchAllTags(desiredTags, actualTags):
    try:
        for desiredTag in desiredTags:
            matched = False
            for actualTag in actualTags:
                if desiredTag.casefold() == actualTag.casefold():
                    matched = True
                    break
            if not matched:
                return False
        return True
    except:
        return False
    
def MatchAnyTag(desiredTags, actualTags):
    try:
        for desiredTag in desiredTags:
            for actualTag in actualTags:
                if desiredTag.casefold() == actualTag.casefold():
                    return True
        return False
    except:
        return False