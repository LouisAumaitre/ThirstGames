from thirst_games.singleton import Singleton


class AbstractGame:
    alive_players = []
    time = None
    going_to_cornucopia = 0

    def death(self, dead_player):
        raise NotImplementedError


class Context(metaclass=Singleton):
    def __init__(self):
        self.game: AbstractGame = None
        self.forbidden_areas = []

    def new_day(self):
        self.forbidden_areas.clear()

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
