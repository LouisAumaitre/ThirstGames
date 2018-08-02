from thirst_games.singleton import Singleton


class Context(metaclass=Singleton):
    def __init__(self):
        self.game = None

    @property
    def alive_players(self):
        return self.game.alive_players

    @property
    def player_count(self) -> int:
        return len(self.alive_players)

    @property
    def time(self):
        return self.game.time

    @property
    def death(self):
        return self.game.death
