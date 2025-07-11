from libStreamDetective.twitch import Twitch

class AllProviders:
    def __init__(self, config):
        self.providers = [Twitch(config)]
        self.games = set()
        self.users = set()
        self.searches = set()
        self.tagsets = dict()
        self.searchAll = False

    def AddGame(self, game:str):
        self.games.add(game)

    def AddUser(self, user:str):
        self.users.add(user)

    def AddSearch(self, query:str):
        self.searches.add(query)
        self.searchAll = True

    def AddTags(self, tags:list):
        tags.sort()
        self.tagsets[' '.join(tags).casefold()] = tags
        self.searchAll = True

    def SearchAll(self):
        self.searchAll = True
    
    def FetchAllStreams(self):
        allGames = {}
        all = []
        allStreamers = {}
        for p in self.providers:
            (games, all_temp, streamers) = p.FetchAllStreams(self.games, self.searchAll, self.users)

            for (k,v) in games.items():
                allGames[k] = v

            all += all_temp

            for (k,v) in streamers.items():
                allStreamers[k] = v

        return (allGames, all, allStreamers)
