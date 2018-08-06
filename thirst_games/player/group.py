from typing import List

from thirst_games.map import Positionable, Area
from thirst_games.narrator import format_list
from thirst_games.player.player import Player
from thirst_games.player.playing_entity import PlayingEntity


class Group(PlayingEntity):
    def __init__(self, players: List[Player]):
        if not len(players):
            raise ValueError
        self.players = players
        self.move_to(players[0].current_area)
        self.map = players[0].map

    def __str__(self):
        return f'G({format_list([p.name for p in self.players])})'

    def think(self):
        strats = {}
        for a in self.players:
            for s, v in a.judge_strats().items():
                strats[s] = strats.get(s, 0) + v
        self.strategy = [s for s, v in strats.items() if v == max(strats.values())][0]
        print(f'{str(self)}:{self.strategy.name}')
        for a in self.players:
            a.strategy = self.strategy

    def act(self):
        for player in self.players:
            player.act()

    def reset_turn(self):
        for p in self.players:
            p.reset_turn()

    @property
    def is_alive(self):
        return sum(p.is_alive for p in self.players) > 0

    def courage(self):
        return max(p.courage for p in self.players)

    def dangerosity(self):
        return sum(p.courage for p in self.players)

    def flee(self, panic=False, drop_verb='drops', stock=False):
        raise NotImplementedError

    def pursue(self):
        raise NotImplementedError

    def enemies(self, area: Area) -> List[Positionable]:
        return [p for p in area.players if p != self]  # TODO: consider

    def set_up_ambush(self):
        raise NotImplementedError

    def estimate_of_power(self, area) -> float:
        raise NotImplementedError

    def estimate_of_danger(self, area) -> float:
        raise NotImplementedError

    def can_see(self, other):
        raise NotImplementedError

    def pillage(self, stuff):
        raise NotImplementedError

    def attack_at_random(self):
        raise NotImplementedError

    def fight(self, other_player):
        raise NotImplementedError
