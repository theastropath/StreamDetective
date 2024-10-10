from libStreamDetective.twitch import Twitch

class AllProviders:
    def __init__(self, config):
        self.providers = [Twitch(config)]
        self.games = set()
        self.users = set()
        self.searches = set()
        self.tagsets = dict()

    def AddGame(self, game:str):
        self.games.add(game)

    def AddUser(self, user:str):
        self.users.add(user)

    def AddSearch(self, query:str):
        self.searches.add(query)

    def AddTags(self, tags:list):
        tags.sort()
        self.tagsets[' '.join(tags).lower()] = tags
    
    def FetchAllStreams(self):
        allGames = {}
        allTags = {}
        allStreamers = {}
        for p in self.providers:
            (games, tags, streamers) = p.FetchAllStreams(self.games, self.tagsets, self.users)

            for (k,v) in games.items():
                allGames[k] = v

            for (k,v) in tags.items():
                allTags[k] = v

            for (k,v) in streamers.items():
                allStreamers[k] = v

        return (allGames, allTags, allStreamers)
