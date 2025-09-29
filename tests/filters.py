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
    def accept(self, entry, streamer='die4ever2011', title=None, tags=None, game=''):
        try:
            name = dictToString(locals())
            ret = CheckStream(entry, streamer, title, tags, game)
            self.assertTrue(ret, 'was supposed to accept: ' + name)
        except Exception as e:
            print('accept failed', e, entry, streamer, title, tags, game)
            raise
    
    def deny(self, entry, streamer='die4ever2011', title=None, tags=None, game=''):
        try:
            name = dictToString(locals())
            ret = CheckStream(entry, streamer, title, tags, game)
            self.assertFalse(ret, 'was supposed to deny: ' + name)
        except Exception as e:
            print('deny failed', e, entry, streamer, title, tags, game)
            raise

    def test_example_configs(self):
        entry = {'filters': GetFilters('DosSpeedruns.json', 0)}
        self.accept(entry, title='T7G speedruns', tags=['speedrun','dos'])
        self.accept(entry, title='MS-DOS game speedruns', tags=['speedrun'])
        self.accept(entry, title='MSDOS game speedrun', tags=['speedrun'])
        self.deny(entry, title='Daily DOSe of DXRando', tags=['speedrun'])

        entry = {'filters': GetFilters('DXRando.json', 0)}
        self.accept(entry, title='playing DXRando')
        self.deny(entry, title='playing random games', tags=[])

    def test_match_words(self):
        filters = [{'MatchWord': 'Deus Ex Randomizer'}]
        entry = {'filters': filters}
        self.accept(entry, title='Deus Ex RaNdomizer Halloween speedruns')

        filters = [{'DontMatchWord': 'Deus Ex Random'}]
        entry = {'filters': filters}
        self.accept(entry, title='Deus Ex RaNdomizer Halloween speedruns')

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
        self.accept(entry, streamer='Die4Ever', title='Deus Ex RaNdomizer Halloween speedruns', tags=['RaNdomizer', 'Speedrun'], game='dEUS eX')

    def negative(self, filters):
        entry = {'filters': filters}
        self.deny(entry, streamer='Bob Page', title='playing some Sonic and other random games and then rule the world', tags=['Sega'], game='sONIC')


def GetFilters(name, num):
    root = Path(__file__).parent.parent
    search:Path = root/'searches_examples'/name
    text = search.read_text()
    data = json.loads(text)
    return data[num]['filters']


def dictToString(d:dict) -> str:
    d = d.copy()
    d.pop('self', None)
    entry = d.pop('entry')
    d2 = {}
    for (k,v) in d.items():
        if v is not None:
            d2[k] = v
    text = repr(d2)
    text += ' --- with filters: ' + repr(entry['filters'])
    return text
