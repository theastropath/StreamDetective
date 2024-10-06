from libStreamDetective.twitch import Twitch

class AllProviders:
    def __init__(self, config):
        self.providers = [Twitch(config)]
        self.games = set()
        self.users = set()

    def AddGame(self, game:str):
        self.games.add(game)

    def AddUser(self, user:str):
        self.users.add(user)
    
    def FetchAllStreams(self):
        allGames = {}
        allStreamers = {}
        for p in self.providers:
            (games, streamers) = p.FetchAllStreams(self.games, self.users)
            for (k,v) in games.items():
                allGames[k] = v
            for (k,v) in streamers.items():
                allStreamers[k] = v
        return (allGames, allStreamers)
