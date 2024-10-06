import re
from libStreamDetective.util import *

def CheckStream(entry, streamer, title, tags, gameName):
    trace("")
    trace("Name: ", streamer, title, tags, gameName, entry)
    if not entry.get('filters'):
        # return True if the filters array is empty, or the key is missing
        trace("no filters, accepting stream")
        return True
    
    if tags:
        tags=[x.lower() for x in tags]
    
    for filter in entry['filters']:
        if CheckStreamFilter(filter, streamer, title, tags, gameName):
            print(streamer, title, tags, gameName, "accepted by filter", filter)
            return True
        trace(streamer, "not accepted by filter", filter)
    debug(streamer, "not accepted by any filters")
    return False


def GetFilter(filter, name) -> list:
    f = filter.get(name, [])
    if not isinstance(f, list):
        f = [f]
    return f


def CheckStreamFilter(filter, streamer, title, tags, gameName):
    if not filter.keys():
        return True

    if not tags:
        tags = []

    for f in GetFilter(filter, 'MatchTag'):
        if f.lower() not in tags:
            return False
    for f in GetFilter(filter, 'MatchTagName'):
        if f.lower() not in tags:
            return False
    for f in GetFilter(filter, 'MatchTagSubstring'):
        found=False
        for tag in tags:
            if f.lower() in tag:
                found=True
        if not found:
            return False
    for f in GetFilter(filter, 'MatchString'):
        if f.lower() not in title.lower():
            return False
    for f in GetFilter(filter, 'DontMatchTag'):
        if f.lower() in tags:
            return False
    for f in GetFilter(filter, 'DontMatchString'):
        if f.lower() in title.lower():
            return False
    for f in GetFilter(filter, 'DontMatchTagName'):
        if f.lower() in tags:
            return False
    for f in GetFilter(filter, 'DontMatchTagSubstring'):
        found=False
        for tag in tags:
            if f.lower() in tag:
                found=True
        if found:
            return False
    for f in GetFilter(filter, 'MatchGameName'):
        if f != gameName:
            return False
    for f in GetFilter(filter, 'DontMatchGameName'):
        if f == gameName:
            return False
    for f in GetFilter(filter, 'DontMatchUser'):
        if f.lower() == streamer.lower():
            return False
        
    for f in GetFilter(filter, 'SearchRegex'):
        found = False
        if re.search(f, title, flags=re.IGNORECASE):
            found = True
        if not found:
            return False
        
    for f in GetFilter(filter, 'DontSearchRegex'):
        if re.search(f, title, flags=re.IGNORECASE):
            return False

    return True
