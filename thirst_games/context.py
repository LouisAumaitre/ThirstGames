from typing import List

from thirst_games.abstract.playing_entity import PlayingEntity
from thirst_games.map import Map
from thirst_games.singleton import Singleton


class AbstractGame:
    alive_players = []
    time = None
    day = 0
    going_to_cornucopia = 0

    def death(self, dead_player):
        raise NotImplementedError

    def playing_entities_at(self, area) -> List[PlayingEntity]:
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
    def day(self):
        return self.game.day

    @property
    def death(self):
        return self.game.death

    def playing_entities_at(self, area) -> List[PlayingEntity]:
        return self.game.playing_entities_at(area)
