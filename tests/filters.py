import unittest
from libStreamDetective.filters import CheckStream

all_filters = {
    'MatchTag': 'Randomizer',
    'MatchTagName': 'Randomizer',
    'MatchTagSubstring': 'Rando',
    'MatchString': 'Randomi',
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
        ret = CheckStream(entry, 'Bob Page', 'playing some Sonic and then rule the world', ['Sega'], 'sONIC')
        self.assertFalse(ret, 'negative')
