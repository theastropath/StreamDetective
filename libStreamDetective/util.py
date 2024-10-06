import random
import traceback
from datetime import datetime

def logex(sd, e: BaseException, *args):
    try:
        estr = "".join(traceback.format_exception(BaseException, e, e.__traceback__))
    except:
        estr = str(e)

    print("\nERROR: "+estr, *args, '\n')
    
    if sd:
        argsStr = " ".join([*args])
        sd.genErrorMsgs("ERROR: "+estr+argsStr)

def fromisoformat(iso):
    # for compatibility with python 3.6
    if not iso:
        return datetime(1970, 1, 1)
    return datetime.strptime(iso, "%Y-%m-%dT%H:%M:%S.%f")


verbose = 1
debug = print
trace = print

def setVerbose(v: int):
    global debug, trace
    verbose = v
    if verbose:
        debug = print
        trace = print
    else:
        debug = lambda *a: None # do-nothing function
        trace = debug
    
    if verbose >= 2:
        trace = print
    else:
        trace = lambda *a: None # do-nothing function

def getVerbose() -> int:
    global verbose
    return verbose

setVerbose(verbose)

def TestStream(testStream):
    return {
        "id": random.randint(1, 999999999), "game_name": testStream['game'],
        "user_id": "123", "user_login": testStream['user'], "user_name": testStream['user'],
        "title": testStream['title'], "tags": testStream.get('tags', [])
    }
