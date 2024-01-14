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
