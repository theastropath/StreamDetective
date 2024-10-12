import unittest
from libStreamDetective.filters import CheckStream
from pathlib import Path
import json

all_filters = {
    'MatchTag': 'Randomizer',
    'MatchTagName': 'Randomizer',
    'MatchTagSubstring': 'Rando',
    'MatchString': 'Randomi',
    'MatchWord': 'Randomizer',
    'DontMatchWord': 'Random',
    'DontMatchTag': 'Sega',
    'DontMatchString': 'Sonic',
    'DontMatchTagName': 'Sega',
    'DontMatchTagSubstring': 'Sega',
    'MatchGameName': 'Deus Ex',
    'DontMatchGameName': 'Sonic',
    'DontMatchUser': 'Bob Page',
    'SearchRegex': 'Randomi(z|s)er',
    'DontSearchRegex': 'Sonic .* rule the world',
}

class TestFilters(unittest.TestCase):
    def test_example_configs(self):
        entry = {'filters': GetFilters('DosSpeedruns.json', 0)}
        ret = CheckStream(entry, 'Die4Ever', 'T7G speedruns', ['speedrun','dos'], 'The 7th Guest')
        self.assertTrue(ret)
        ret = CheckStream(entry, 'Die4Ever', 'MS-DOS game speedruns', ['speedrun'], 'The 7th Guest')
        self.assertTrue(ret)
        ret = CheckStream(entry, 'Die4Ever', 'MSDOS game speedrun', ['speedrun'], 'The 7th Guest')
        self.assertTrue(ret)
        ret = CheckStream(entry, 'Die4Ever', 'Daily DOSe of DXRando', ['speedrun'], 'Deus Ex Randomizer')
        self.assertFalse(ret)

    def test_match_words(self):
        filters = [{'MatchWord': 'Deus Ex Randomizer'}]
        entry = {'filters': filters}
        ret = CheckStream(entry, 'Die4Ever', 'Deus Ex RaNdomizer Halloween speedruns', ['RaNdomizer', 'Speedrun'], 'dEUS eX')
        self.assertTrue(ret)

        filters = [{'DontMatchWord': 'Deus Ex Random'}]
        entry = {'filters': filters}
        ret = CheckStream(entry, 'Die4Ever', 'Deus Ex RaNdomizer Halloween speedruns', ['RaNdomizer', 'Speedrun'], 'dEUS eX')
        self.assertTrue(ret)

    def test_single_filters(self):
        for (k,v) in all_filters.items():
            with self.subTest(k+':'+v):
                filters = [{k:v}]
                self.positive(filters)
                self.negative(filters)
    
    def test_double_filters(self):
        for k1 in all_filters.keys():
            for k2 in all_filters.keys():
                if k1==k2:
                    continue
                self.double_filters(k1, k2)

    def double_filters(self, k1, k2):
        filters = []
        filters.append({k1: all_filters[k1]})
        filters.append({k2: all_filters[k2]})
        with self.subTest(repr(filters)):
            self.positive(filters)
            self.negative(filters)

    def positive(self, filters):
        entry = {'filters': filters}
        ret = CheckStream(entry, 'Die4Ever', 'Deus Ex RaNdomizer Halloween speedruns', ['RaNdomizer', 'Speedrun'], 'dEUS eX')
        self.assertTrue(ret, 'positive')

    def negative(self, filters):
        entry = {'filters': filters}
        ret = CheckStream(entry, 'Bob Page', 'playing some Sonic and other random games and then rule the world', ['Sega'], 'sONIC')
        self.assertFalse(ret, 'negative')


def GetFilters(name, num):
    root = Path(__file__).parent.parent
    search:Path = root/'searches_examples'/name
    text = search.read_text()
    data = json.loads(text)
    return data[num]['filters']

