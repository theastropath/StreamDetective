import argparse
from libStreamDetective.util import setVerbose

parser = argparse.ArgumentParser()
parser.add_argument('-v', '--verbose', action='count', default=0)
parser.add_argument('-d', '--dry-run', action="store_true")
parser.add_argument('-u', '--user')
parser.add_argument('-g', '--game')
parser.add_argument('-t', '--title')
parser.add_argument('-s', '--user-status')
parser.add_argument('-f', '--search-file', help='Specify one of the JSON search files to use and ignore the rest. Example: --search-file=DXRando.json')
args = parser.parse_args()
setVerbose(args.verbose) # HACK: need to do this before importing everything

from libStreamDetective.libStreamDetective import *
if args.title:
    print('using test stream from CLI args:', args)
    sd = StreamDetective(True, testStream=TestStream({
        'user': args.user, 'game': args.game, 'title': args.title
    }))
    exit(0)
elif args.user_status:
    print('checking status of user:', args.user_status)
    sd = StreamDetective(True, checkUser=args.user_status)
    exit(0)

sd = StreamDetective(args.dry_run, searchFile=args.search_file)
