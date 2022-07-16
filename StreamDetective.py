import argparse
from libStreamDetective.libStreamDetective import *

parser = argparse.ArgumentParser()
parser.add_argument('-v', '--verbose', action='count', default=0)
parser.add_argument('-d', '--dry-run', action="store_true")
args = parser.parse_args()
setVerbose(args.verbose)

sd = StreamDetective(args.dry_run)
