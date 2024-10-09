from datetime import datetime
import os
from libStreamDetective.util import *


def HandleFilters(self, search, allStreams):
    newStreams = []
    now = datetime.now()

    for stream in allStreams:
        streamer = stream['user_login']
        title = stream['title']
        tags = stream['tags']
        stream['last_seen'] = now.isoformat()
        matched = self.CheckStream(search, streamer, title, tags, stream["game_name"])
        if matched:
            debug("matched "+streamer)
            stream['last_matched'] = now.isoformat()
            newStreams.append(stream)
        else:
            trace('didn\'t match', streamer)
            
    # All stream info now retrieved
    if newStreams:
        print("  Matched Streams: "+str([stream['user_login'] for stream in newStreams]))
        self.genNotifications(newStreams, search)
    
    debug("\n\n")
    return newStreams
