from typing import List

from thirst_games.map import Area, Positionable
from thirst_games.player.fighter import FightingEntity


class PlayingEntity(FightingEntity):
    strategy = None
    acted = False

    def think(self):
        raise NotImplementedError

    def act(self):
        raise NotImplementedError

    def reset_turn(self):
        self.strategy = None
        self.acted = False

    @property
    def is_alive(self):
        raise NotImplementedError

    def courage(self):
        raise NotImplementedError

    def dangerosity(self):
        raise NotImplementedError

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


class Strategy:
    def __init__(self, name, pref, action):
        self.name = name
        self.pref = pref
        self.action = action

    def apply(self, player):
        out = self.action(player)
        if isinstance(out, str):
            print(f'{player.first_name} {out}')