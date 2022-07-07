import argparse
from libStreamDetective.libStreamDetective import *

parser = argparse.ArgumentParser()
parser.add_argument('-v', '--verbose', action='count', default=0)
args = parser.parse_args()
setVerbose(args.verbose)

sd = StreamDetective()
