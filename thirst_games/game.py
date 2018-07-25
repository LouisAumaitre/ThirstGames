from thirst_games.map import Map


class Game:
    def __init__(self, players: list):
        self.players = players
        self.alive_players = players
        self.map = Map()
        for p in self.players:
            self.map.add_player(p)

    def run(self):
        day = 1
        while len(self.alive_players) > 1 or day < 10:
            print(f'== DAY {day} ==')
            self.day()

    def day(self):
        pass
